import logging
from typing import List, Dict, Any, Optional
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

logger = logging.getLogger(__name__)

class CrossEncoderReranker:
    """
    Reranks a list of retrieved chunks using a Cross-Encoder model.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            if CrossEncoder is not None:
                self.model = CrossEncoder(model_name)
                logger.info(f"CrossEncoder initialized with model: {model_name}")
            else:
                logger.warning("sentence_transformers not installed. Reranker fallback active.")
                self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize CrossEncoder: {e}")
            self.model = None

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks chunks based on their relevance to the query.
        """
        if not self.model or not chunks:
            return chunks[:top_k]

        # Prepare pairs: (query, chunk_content)
        pairs = [[query, chunk.get("content", "")] for chunk in chunks]

        try:
            scores = self.model.predict(pairs)

            # Pair chunks with their scores
            scored_chunks = zip(chunks, scores)

            # Sort by score descending
            sorted_chunks = sorted(scored_chunks, key=lambda x: x[1], reverse=True)

            # Return top K
            return [chunk for chunk, score in sorted_chunks[:top_k]]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return chunks[:top_k]
