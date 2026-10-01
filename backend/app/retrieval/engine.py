import logging
from typing import List, Dict, Any, Optional
from backend.app.ingestion.embedder import JinaEmbedder
from backend.app.retrieval.vector_store import RetrievalVectorStore
from backend.app.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)

class RetrievalEngine:
    """
    Coordinates the end-to-end retrieval flow:
    Embedding -> Hybrid Search -> Reranking.
    """

    def __init__(self, embedder: JinaEmbedder, vector_store: RetrievalVectorStore, reranker: CrossEncoderReranker):
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker

    def retrieve(self, tenant_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most relevant chunks for a tenant's query.
        """
        logger.info(f"Retrieving for tenant {tenant_id} with query: {query}")

        try:
            # 1. Generate query embedding (Strictly retrieval.query task)
            query_vector = self.embedder.embed([query], task="retrieval.query")[0]

            # 2. Hybrid Search (Dense + Sparse)
            # We retrieve more than 'limit' to allow the reranker to filter
            candidates = self.vector_store.search_hybrid(
                tenant_id=tenant_id,
                query_text=query,
                query_vector=query_vector,
                limit=limit * 4
            )

            if not candidates:
                logger.info("No candidates found during hybrid search.")
                return []

            # 3. Cross-Encoder Reranking
            final_results = self.reranker.rerank(
                query=query,
                chunks=candidates,
                top_k=limit
            )

            return final_results

        except Exception as e:
            logger.error(f"Retrieval engine failed for tenant {tenant_id}: {e}")
            return []
