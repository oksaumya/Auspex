"""2. Context Retrieval Node — Qdrant hybrid search + Cohere rerank."""
import logging
from typing import Any, Dict

from core.config import DEMO_DIR
from graph.state import GraphState
from retrieval.reranker import get_reranker
from retrieval.vector_store import get_retriever

logger = logging.getLogger("Node.Retrieval")


def context_retrieval_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Executing Context Retrieval Node...")
    retriever = get_retriever()
    reranker = get_reranker()

    for filename in ("auth.py", "utils.py"):
        filepath = DEMO_DIR / filename
        if filepath.exists():
            retriever.index_file(f"fixtures/demo_files/{filename}", filepath.read_text())

    retrieved_context = {}
    for f_info in state["changed_files"]:
        path = f_info["path"]
        patch = f_info["patch"]
        query = f"Code block: {patch}"

        results = retriever.hybrid_search(query, limit=5)
        reranked = reranker.rerank(query, results, top_n=2)
        retrieved_context[path] = [item["content"] for item in reranked]
        logger.info("Retrieved %d context chunks for %s", len(reranked), path)

    return {"retrieved_context": retrieved_context, "status": "retrieved"}
