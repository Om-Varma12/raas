import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from app.retrieval.vector_store import RetrievalVectorStore
    from app.retrieval.reranker import CrossEncoderReranker
    from app.retrieval.engine import RetrievalEngine
    from app.ingestion.embedder import JinaEmbedder
except ImportError:
    from backend.app.retrieval.vector_store import RetrievalVectorStore
    from backend.app.retrieval.reranker import CrossEncoderReranker
    from backend.app.retrieval.engine import RetrievalEngine
    from backend.app.ingestion.embedder import JinaEmbedder


class TestRetrieval(unittest.TestCase):

    def setUp(self):
        self.mock_qdrant = MagicMock()
        self.vector_store = RetrievalVectorStore()
        self.vector_store.client = self.mock_qdrant

    def test_search_dense_formatting(self):
        mock_hit = MagicMock()
        mock_hit.payload = {"chunk_id": "chunk_1", "content": "Sample content", "tenant_id": "tenant-123"}
        self.mock_qdrant.search.return_value = [mock_hit]

        results = self.vector_store.search_dense("tenant-123", [0.1] * 1024, limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "chunk_1")
        self.mock_qdrant.search.assert_called_once_with(
            collection_name="tenant-123",
            query_vector=("dense", [0.1] * 1024),
            limit=5,
            with_payload=True
        )

    def test_hybrid_search_rrf_fusion(self):
        hit1 = MagicMock()
        hit1.payload = {"chunk_id": "c1", "content": "Python async docs"}
        hit2 = MagicMock()
        hit2.payload = {"chunk_id": "c2", "content": "FastAPI dependencies"}

        self.mock_qdrant.search.side_effect = [
            [hit1, hit2], # dense results
            [hit2]        # sparse results
        ]

        results = self.vector_store.search_hybrid(
            tenant_id="tenant-dev",
            query_text="python async",
            query_vector=[0.1] * 1024,
            limit=2
        )

        self.assertEqual(len(results), 2)
        # hit2 appeared in both dense and sparse, so RRF score should rank hit2 first
        self.assertEqual(results[0]["chunk_id"], "c2")

    def test_retrieval_engine_flow(self):
        mock_embedder = MagicMock(spec=JinaEmbedder)
        mock_embedder.embed.return_value = [[0.1] * 1024]

        mock_vector_store = MagicMock(spec=RetrievalVectorStore)
        mock_vector_store.search_hybrid.return_value = [
            {"chunk_id": "c1", "content": "Document 1"},
            {"chunk_id": "c2", "content": "Document 2"}
        ]

        mock_reranker = MagicMock(spec=CrossEncoderReranker)
        mock_reranker.rerank.side_effect = lambda query, chunks, top_k: chunks[:top_k]

        engine = RetrievalEngine(
            embedder=mock_embedder,
            vector_store=mock_vector_store,
            reranker=mock_reranker
        )

        results = engine.retrieve(tenant_id="tenant-dev", query="How to configure CORS?", limit=2)
        self.assertEqual(len(results), 2)
        mock_embedder.embed.assert_called_once_with(["How to configure CORS?"], task="retrieval.query")
        mock_vector_store.search_hybrid.assert_called_once()
        mock_reranker.rerank.assert_called_once()


if __name__ == "__main__":
    unittest.main()
