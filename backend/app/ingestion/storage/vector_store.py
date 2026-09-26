from typing import List, Dict, Any, Optional
import uuid

class VectorStoreWrapper:
    """
    Wrapper for the vector database (Qdrant/pgvector).
    Ensures that every write is strictly scoped to a tenant_id.
    """

    def __init__(self, connection_string: Optional[str] = None):
        # In a real implementation, this would initialize the QdrantClient or
        # a SQLAlchemy session for pgvector.
        self.connection_string = connection_string or "mock://localhost:6333"
        # Local storage for mock verification
        self._storage: Dict[str, List[Dict[str, Any]]] = {}

    def store_chunks(self, tenant_id: str, chunks: List[Dict[str, Any]]):
        """
        Stores chunks for a specific tenant.
        Every chunk must have the tenant_id associated with it.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for all vector store operations.")

        # Create a collection for the tenant if it doesn't exist (simplified logic)
        if tenant_id not in self._storage:
            self._storage[tenant_id] = []

        for chunk in chunks:
            # Enforce tenant_id inside the payload as per SCHEMA.md
            payload = chunk.get("metadata", {})
            if "tenant_id" not in payload:
                payload["tenant_id"] = tenant_id

            # In a real implementation, we would use Qdrant's upsert method:
            # client.upsert(collection_name=f"tenant_{tenant_id}", points=...)

            chunk_data = {
                "id": str(uuid.uuid4()),
                "vector": chunk.get("vector"),
                "payload": payload,
                "content": chunk.get("content")
            }
            self._storage[tenant_id].append(chunk_data)

    def get_tenant_chunks(self, tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves chunks for a specific tenant.
        Used primarily for leak-test assertions.
        """
        return self._storage.get(tenant_id, [])[:limit]
