import os
import requests
import time
import logging
from typing import List, Literal, Dict, Any, Optional
from .caching.embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)

# Define the task types as per TECHNICALS.md
# Ingestion (chunk embedding) -> retrieval.passage
# Query (user question embedding) -> retrieval.query
TaskType = Literal["retrieval.passage", "retrieval.query"]

class JinaEmbedder:
    """
    Wrapper for Jina Embeddings API with support for task types and caching.
    Includes rate-limiting and exponential backoff to handle 429 errors.
    """

    def __init__(self, api_key: Optional[str] = None, cache: Optional[EmbeddingCache] = None):
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        self.url = "https://api.jina.ai/v1/embeddings"
        self.cache = cache or EmbeddingCache()
        # Rate limit tracking: 100 RPM = 1 request every ~0.6 seconds
        self._last_call_time = 0.0
        self._min_interval = 0.65 # slightly over 0.6s to stay safe (< 90 RPM)

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
        if task == "retrieval.passage":
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached:
                    results.append(cached)
                else:
                    results.append(None)
                    texts_to_embed.append(text)
        else:
            texts_to_embed = texts
            results = [None] * len(texts)

        # 2. Batch API call for missing embeddings
        if texts_to_embed:
            # Smaller batch size (25) to stay within Jina API token-per-minute limits
            # and avoid request timeouts on large text blocks.
            batch_size = 25
            all_api_embeddings = []

            for i in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[i : i + batch_size]
                logger.info(f"Requesting embeddings for batch {i//batch_size + 1} ({len(batch)} texts)")
                all_api_embeddings.extend(self._call_api_with_retry(batch, task))

            # Merge API results back into the results list
            api_idx = 0
            for i in range(len(results)):
                if results[i] is None:
                    val = all_api_embeddings[api_idx]
                    results[i] = val
                    if task == "retrieval.passage":
                        self.cache.set(texts[i], val)
                    api_idx += 1

        return results

    def _call_api_with_retry(self, texts: List[str], task: TaskType) -> List[List[float]]:
        """
        Call Jina API with rate limiting and exponential backoff for 429 errors.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "jina-embeddings-v4",
            "task": task,
            "input": [{"text": t} for t in texts],
            "dimensions": 1024,
            "normalized": True
        }

        max_retries = 5
        retry_delay = 2.0  # Initial delay in seconds

        for attempt in range(max_retries):
            # Enforce minimum interval between requests to stay under 90 RPM
            now = time.time()
            elapsed = now - self._last_call_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

            try:
                response = requests.post(self.url, headers=headers, json=data, timeout=60)
                self._last_call_time = time.time()

                if response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit (429). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return [item["embedding"] for item in response.json().get("data", [])]

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                wait_time = retry_delay * (2 ** attempt)
                logger.error(f"API request failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

        raise Exception("Max retries exceeded for Jina API")
