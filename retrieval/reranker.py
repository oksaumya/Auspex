import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("Reranker")

class CohereReranker:
    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY")
        self._client = None
        if not self.api_key or "your_" in self.api_key:
            self.api_key = None
            logger.warning("COHERE_API_KEY environment variable not found or placeholder. Reranking will use pass-through/mock mode.")
        else:
            try:
                import cohere
                # Initialize v5 Cohere Client
                self._client = cohere.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Cohere Client: {e}. Falling back to pass-through mode.")

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        """Reranks retrieved document chunks using Cohere or fallback logic."""
        if not documents:
            return []

        if not self._client:
            # Fallback pass-through: already ordered by hybrid retriever
            logger.info("Using pass-through rerank logic (Cohere not configured or initialized).")
            return documents[:top_n]

        try:
            # Format text documents for Cohere
            doc_texts = [doc["content"] for doc in documents]
            
            # Call Cohere Rerank API
            response = self._client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=doc_texts,
                top_n=top_n
            )
            
            reranked_docs = []
            for result in response.results:
                original_doc = documents[result.index]
                # Include Cohere relevance score
                original_doc["relevance_score"] = float(result.relevance_score)
                reranked_docs.append(original_doc)
                
            logger.info(f"Successfully reranked {len(documents)} docs with Cohere. Top score: {reranked_docs[0].get('relevance_score', 0.0) if reranked_docs else 0.0}")
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Error calling Cohere Rerank API: {e}. Falling back to pass-through.")
            return documents[:top_n]

_reranker = None

def get_reranker() -> CohereReranker:
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker
