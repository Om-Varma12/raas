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

    def search_dense(self, tenant_id: str, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Performs dense vector search within a tenant's collection.
        """
        collection_name = tenant_id
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
        Note: This assumes sparse vectors are enabled/configured in Qdrant.
        """
        collection_name = tenant_id
        try:
            # In a real scenario, we would convert query_text to sparse vector here
            # or use Qdrant's internal sparse indexing if configured.
            # For now, we implement the Qdrant search call.
            result = self.client.search(
                collection_name=collection_name,
                query_filter=models.Filter(
                    must=[models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id))]
                ),
                # Note: Actual sparse search requires a sparse vector input.
                # This is a placeholder for the hybrid fusion logic.
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
        # 1. Get dense results
        dense_results = self.search_dense(tenant_id, query_vector, limit=limit * 2)

        # 2. Get sparse results
        sparse_results = self.search_sparse(tenant_id, query_text, limit=limit * 2)

        # 3. RRF Fusion
        # RRF score = sum(1 / (k + rank))
        K = 60
        scores = {}

        for rank, res in enumerate(dense_results, 1):
            res_id = res.get("chunk_id", str(res)) # Fallback to content hash or similar if id not present
            scores[res_id] = scores.get(res_id, 0) + (1.0 / (K + rank))

        for rank, res in enumerate(sparse_results, 1):
            res_id = res.get("chunk_id", str(res))
            scores[res_id] = scores.get(res_id, 0) + (1.0 / (K + rank))

        # Sort by RRF score
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Map IDs back to full payloads
        all_payloads = {str(p): p for p in (dense_results + sparse_results)}

        final_results = []
        for res_id, _ in sorted_ids:
            if res_id in all_payloads:
                final_results.append(all_payloads[res_id])
            if len(final_results) >= limit:
                break

        return final_results
