from typing import Dict, Optional
import hashlib

class EmbeddingCache:
    """
    Content-hash based cache to skip re-embedding identical chunks.
    As per PRD.md, this is the third layer of caching.
    """

    def __init__(self):
        # In a real implementation, this would be backed by Redis or Postgres.
        # Using a local dict for the foundational implementation.
        self._cache: Dict[str, List[float]] = {}

    def get_hash(self, content: str) -> str:
        """Generate a SHA-256 hash of the content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def get(self, content: str) -> Optional[List[float]]:
        content_hash = self.get_hash(content)
        return self._cache.get(content_hash)

    def set(self, content: str, embedding: List[float]):
        content_hash = self.get_hash(content)
        self._cache[content_hash] = embedding
