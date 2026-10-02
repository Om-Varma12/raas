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

    def _ensure_collection(self, collection_name: str, vector_size: int = 1024):
        """
        Creates a Qdrant collection if it doesn't exist or recreates if size mismatches.
        """
        try:
            info = self.client.get_collection(collection_name=collection_name)
            dense_cfg = info.config.params.vectors.get("dense") if isinstance(info.config.params.vectors, dict) else info.config.params.vectors
            existing_size = getattr(dense_cfg, "size", None)
            if existing_size and existing_size != vector_size:
                logger.info(f"Recreating collection {collection_name} due to dimension mismatch ({existing_size} vs {vector_size})")
                self.client.delete_collection(collection_name=collection_name)
                import time
                time.sleep(0.5)
                raise ValueError("Dimension mismatch")
        except Exception:
            logger.info(f"Creating new collection: {collection_name}")
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE
                        )
                    }
                )
            except Exception as err:
                err_msg = str(err)
                if hasattr(err, "response") and getattr(err.response, "content", None):
                    err_msg += " " + str(err.response.content)
                if "File exists" in err_msg or "os error 17" in err_msg:
                    logger.warning(f"Orphaned collection folder detected for {collection_name}. Deleting and recreating...")
                    try:
                        self.client.delete_collection(collection_name=collection_name)
                        import time
                        time.sleep(0.5)
                    except Exception:
                        pass
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config={
                            "dense": models.VectorParams(
                                size=vector_size,
                                distance=models.Distance.COSINE
                            )
                        }
                    )
                else:
                    raise err

    def store_chunks(self, collection_name: str, chunks: List[Dict[str, Any]], tenant_id: Optional[str] = None):
        """
        Stores chunks in the specified collection using deterministic IDs for evaluation consistency.
        """
        if not collection_name:
            raise ValueError("collection_name is required.")

        tenant_id = tenant_id or collection_name

        self._ensure_collection(collection_name)

        points = []
        for chunk in chunks:
            payload = chunk.get("metadata", {}).copy()
            payload["tenant_id"] = tenant_id
            payload["content"] = chunk.get("content")

            # Deterministic ID generation: uuid5(NAMESPACE_DNS, string)
            # Formula: f"{tenant_id}|{doc_path}|{content_hash}"
            # doc_path might be in metadata; fallback to content_hash
            doc_path = payload.get("doc_path", "unknown_path")
            content_hash = payload.get("content_hash", "")

            unique_string = f"{tenant_id}|{doc_path}|{content_hash}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": chunk.get("vector"),
                    },
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def get_tenant_chunks(self, collection_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves chunks from a specific collection.
        """
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
