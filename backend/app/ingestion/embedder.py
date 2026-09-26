import os
import requests
from typing import List, Literal, Dict, Any, Optional
from .caching.embedding_cache import EmbeddingCache

# Define the task types as per TECHNICALS.md
# Ingestion (chunk embedding) -> retrieval.passage
# Query (user question embedding) -> retrieval.query
TaskType = Literal["retrieval.passage", "retrieval.query"]

class JinaEmbedder:
    """
    Wrapper for Jina Embeddings API with support for task types and caching.
    """

    def __init__(self, api_key: Optional[str] = None, cache: Optional[EmbeddingCache] = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.url = "https://api.jina.ai/v1/embeddings"
        self.cache = cache or EmbeddingCache()

    def embed(self, texts: List[str], task: TaskType = "retrieval.passage") -> List[List[float]]:
        """
        Generates embeddings for the given texts.
        Checks the embedding cache first for 'retrieval.passage' tasks.
        """
        if not self.api_key:
            raise ValueError("JINA_API_KEY not found in environment or constructor.")

        results = []
        texts_to_embed = []

        # 1. Cache lookup for passages
        # Only cache passage embeddings because query embeddings are transient.
        if task == "retrieval.passage":
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached:
                    results.append(cached)
                else:
                    # Placeholder for the results list to maintain order
                    results.append(None)
                    texts_to_embed.append(text)
        else:
            # For retrieval.query, we always embed
            texts_to_embed = texts
            results = [None] * len(texts)

        # 2. Batch API call for missing embeddings
        if texts_to_embed:
            embeddings = self._call_api(texts_to_embed, task)

            # Merge API results back into the results list
            api_idx = 0
            for i in range(len(results)):
                if results[i] is None:
                    val = embeddings[api_idx]
                    results[i] = val
                    # Store in cache if it's a passage
                    if task == "retrieval.passage":
                        self.cache.set(texts[i], val)
                    api_idx += 1

        return results

    def _call_api(self, texts: List[str], task: TaskType) -> List[List[float]]:
        """
        Actual HTTP call to Jina API.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Dimensions truncated to 1024 as per TECHNICALS.md
        data = {
            "model": "jina-embeddings-v4",
            "task": task,
            "input": [{"text": t} for t in texts],
            "dimensions": 1024,
            "normalized": True
        }

        response = requests.post(self.url, headers=headers, json=data)
        response.raise_for_status()

        # Extract the embeddings from the response
        # Expected response format: {"data": [{"embedding": [...], ...}, ...]}
        return [item["embedding"] for item in response.json().get("data", [])]
