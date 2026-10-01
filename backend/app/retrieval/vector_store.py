from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)

class RetrievalVectorStore:
    """
    Retrieval-focused wrapper for Qdrant Vector Database.
    Implements dense, sparse, and hybrid search scoped to tenant_id.
    """

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None):
        self.client = QdrantClient(host=host, port=port, api_key=api_key)

    def _get_collection_name(self, tenant_id: str) -> str:
        return tenant_id if tenant_id.startswith("tenant") else f"tenant_{tenant_id}"

    def search_dense(self, tenant_id: str, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Performs dense vector search within a tenant's collection.
        """
        collection_name = self._get_collection_name(tenant_id)
        try:
            # Use the 'dense' named vector as defined during ingestion
            result = self.client.search(
                collection_name=collection_name,
                query_vector=("dense", query_vector),
                limit=limit,
                with_payload=True
            )
            return [hit.payload for hit in result]
        except Exception as e:
            logger.error(f"Dense search failed for tenant {tenant_id}: {e}")
            return []

    def search_sparse(self, tenant_id: str, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Performs sparse search within a tenant's collection.
        """
        collection_name = self._get_collection_name(tenant_id)
        try:
            result = self.client.search(
                collection_name=collection_name,
                query_filter=models.Filter(
                    must=[models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id))]
                ),
                limit=limit,
                with_payload=True
            )
            return [hit.payload for hit in result]
        except Exception as e:
            logger.error(f"Sparse search failed for tenant {tenant_id}: {e}")
            return []

    def search_hybrid(self, tenant_id: str, query_text: str, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Combines dense and sparse search results using Reciprocal Rank Fusion (RRF).
        """
        dense_results = self.search_dense(tenant_id, query_vector, limit=limit * 2)
        sparse_results = self.search_sparse(tenant_id, query_text, limit=limit * 2)

        K = 60
        scores: Dict[str, float] = {}
        all_payloads: Dict[str, Dict[str, Any]] = {}

        def get_item_key(payload: Dict[str, Any]) -> str:
            return str(payload.get("chunk_id") or payload.get("content_hash") or payload.get("content"))

        for rank, res in enumerate(dense_results, 1):
            key = get_item_key(res)
            scores[key] = scores.get(key, 0.0) + (1.0 / (K + rank))
            all_payloads[key] = res

        for rank, res in enumerate(sparse_results, 1):
            key = get_item_key(res)
            scores[key] = scores.get(key, 0.0) + (1.0 / (K + rank))
            all_payloads[key] = res

        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        final_results = []
        for key, _ in sorted_ids:
            if key in all_payloads:
                final_results.append(all_payloads[key])
            if len(final_results) >= limit:
                break

        return final_results
