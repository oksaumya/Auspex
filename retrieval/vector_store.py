import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from rank_bm25 import BM25Okapi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VectorStore")

class HybridRetriever:
    def __init__(self):
        # Setup in-memory Qdrant Client
        self.qdrant_client = QdrantClient(":memory:")
        self.collection_name = "codebase"
        self.vector_size = 384 # Dimension for 'all-MiniLM-L6-v2'
        
        # Initialize collection
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )
        
        # Local model for embeddings (lazy initialized)
        self._encoder = None
        self.documents: List[Dict[str, Any]] = [] # Track original docs
        self.bm25: Optional[BM25Okapi] = None
        self.indexed_files = set()

    @property
    def encoder(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformers: {e}. Falling back to mock embeddings.")
                self._encoder = "mock"
        return self._encoder

    def _get_embedding(self, text: str) -> List[float]:
        encoder = self.encoder
        if encoder == "mock":
            # Generate stable mock embedding based on hash
            import hashlib
            h = hashlib.md5(text.encode()).digest()
            emb = []
            for i in range(self.vector_size):
                idx = i % len(h)
                emb.append(float(h[idx]) / 255.0)
            return emb
        else:
            return encoder.encode(text).tolist()

    def split_code(self, filepath: str, content: str) -> List[Dict[str, Any]]:
        """Splits code file content into logical paragraphs or functions."""
        lines = content.splitlines()
        chunks = []
        chunk_size = 25
        chunk_overlap = 5
        
        # Simple sliding window chunker
        for i in range(0, len(lines), chunk_size - chunk_overlap):
            chunk_lines = lines[i:i + chunk_size]
            if not chunk_lines:
                break
            chunk_text = "\n".join(chunk_lines)
            chunks.append({
                "id": str(uuid.uuid4()),
                "filepath": filepath,
                "start_line": i + 1,
                "end_line": i + len(chunk_lines),
                "content": chunk_text
            })
            if i + chunk_size >= len(lines):
                break
        return chunks

    def index_file(self, filepath: str, content: str):
        """Indexes a single file's contents into Qdrant & BM25."""
        if not content.strip() or filepath in self.indexed_files:
            return
            
        chunks = self.split_code(filepath, content)
        if not chunks:
            return
            
        points_ids = []
        points_vectors = []
        points_payloads = []
        
        for chunk in chunks:
            emb = self._get_embedding(chunk["content"])
            points_ids.append(chunk["id"])
            points_vectors.append(emb)
            points_payloads.append({
                "filepath": chunk["filepath"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "content": chunk["content"]
            })
            # Track documents globally for BM25
            self.documents.append(chunk)

        # Upload to Qdrant
        self.qdrant_client.upload_collection(
            collection_name=self.collection_name,
            ids=points_ids,
            vectors=points_vectors,
            payload=points_payloads
        )
        
        # Re-build BM25 index with tokenized code chunks
        tokenized_corpus = [doc["content"].lower().split() for doc in self.documents]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)
            
        self.indexed_files.add(filepath)
        logger.info(f"Indexed {len(chunks)} chunks from file: {filepath}")

    def hybrid_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs a Hybrid Search using Qdrant (dense) + BM25 (sparse) with RRF fusion."""
        if not self.documents:
            return []

        # 1. Dense Search (qdrant-client >= 1.10 uses query_points)
        query_vector = self._get_embedding(query)
        dense_response = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit * 2,
            with_payload=True,
        )
        dense_results = dense_response.points

        # Rank by dense position
        dense_ranks = {res.payload["content"]: idx for idx, res in enumerate(dense_results)}

        # 2. Sparse Search (BM25)
        sparse_ranks = {}
        if self.bm25:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            # Pair scores with original document index
            scored_docs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            for rank, (doc_idx, score) in enumerate(scored_docs[:limit * 2]):
                doc_content = self.documents[doc_idx]["content"]
                sparse_ranks[doc_content] = rank

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF formula: Score = 1 / (60 + DenseRank) + 1 / (60 + SparseRank)
        k = 60
        rrf_scores = {}
        content_to_meta = {}

        # Cache payload maps from dense results
        for res in dense_results:
            content_to_meta[res.payload["content"]] = {
                "filepath": res.payload["filepath"],
                "start_line": res.payload["start_line"],
                "end_line": res.payload["end_line"],
                "content": res.payload["content"],
                "score_dense": res.score
            }

        # Cache payload maps from BM25 doc indexes
        if self.bm25:
            for doc_idx, score in scored_docs[:limit * 2]:
                doc = self.documents[doc_idx]
                if doc["content"] not in content_to_meta:
                    content_to_meta[doc["content"]] = {
                        "filepath": doc["filepath"],
                        "start_line": doc["start_line"],
                        "end_line": doc["end_line"],
                        "content": doc["content"],
                        "score_dense": 0.0
                    }

        # Compute RRF score for elements found in either
        all_contents = set(dense_ranks.keys()).union(set(sparse_ranks.keys()))
        for content in all_contents:
            dr = dense_ranks.get(content, 1e9)
            sr = sparse_ranks.get(content, 1e9)
            rrf_score = (1.0 / (k + dr)) + (1.0 / (k + sr))
            rrf_scores[content] = rrf_score

        # Sort all chunks by RRF score descending
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for content, rrf_score in sorted_chunks[:limit]:
            meta = content_to_meta[content]
            meta["rrf_score"] = rrf_score
            results.append(meta)
            
        return results

# Singleton retriever instance
_retriever = None

def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
