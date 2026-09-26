from typing import List, Dict, Any, Optional
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)

class VectorStoreWrapper:
    """
    Wrapper for Qdrant Vector Database.
    Ensures that every write is strictly scoped to a tenant_id.
    """

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None):
        self.client = QdrantClient(host=host, port=port, api_key=api_key)

    def _ensure_collection(self, tenant_id: str):
        """
        Creates a Qdrant collection for the tenant if it doesn't exist.
        Configured as per docs/SCHEMA.md.
        """
        collection_name = f"tenant_{tenant_id}"

        try:
            self.client.get_collection(collection_name=collection_name)
        except Exception:
            logger.info(f"Creating new collection for tenant: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": models.VectorParams(
                        size=1024, # Jina truncated dimension from TECHNICALS.md
                        distance=models.Distance.COSINE
                    ),
                    "sparse": models.SparseVectorParams() # For hybrid search
                }
            )

    def store_chunks(self, tenant_id: str, chunks: List[Dict[str, Any]]):
        """
        Stores chunks for a specific tenant in their dedicated collection.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for all vector store operations.")

        self._ensure_collection(tenant_id)
        collection_name = f"tenant_{tenant_id}"

        points = []
        for chunk in chunks:
            # Enforce tenant_id inside the payload as per SCHEMA.md
            payload = chunk.get("metadata", {}).copy()
            payload["tenant_id"] = tenant_id
            payload["content"] = chunk.get("content") # Store content for retrieval

            point_id = str(uuid.uuid4())

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": chunk.get("vector"),
                        # Sparse vectors would be added here in the HybridSearch phase
                    },
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def get_tenant_chunks(self, tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves chunks for a specific tenant.
        Used primarily for leak-test assertions.
        """
        collection_name = f"tenant_{tenant_id}"
        try:
            result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            return [point.payload for point in result[0]]
        except Exception:
            return []
