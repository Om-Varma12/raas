import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from app.agents.graph import RAGGraph
    from app.agents.router_agent import RouterAgent
    from app.agents.decomposer_agent import DecomposerAgent
    from app.agents.retrieval_agent import RetrievalAgent
    from app.agents.verifier_agent import VerifierAgent
    from app.retrieval.engine import RetrievalEngine
except ImportError:
    from backend.app.agents.graph import RAGGraph
    from backend.app.agents.router_agent import RouterAgent
    from backend.app.agents.decomposer_agent import DecomposerAgent
    from backend.app.agents.retrieval_agent import RetrievalAgent
    from backend.app.agents.verifier_agent import VerifierAgent
    from backend.app.retrieval.engine import RetrievalEngine


class TestAgenticGraph(unittest.TestCase):

    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_engine = MagicMock(spec=RetrievalEngine)
        self.mock_engine.retrieve.return_value = [
            {"chunk_id": "c1", "content": "FastAPI is a modern python web framework.", "content_hash": "hash1"}
        ]
        self.rag_graph = RAGGraph(llm_client=self.mock_llm, retrieval_engine=self.mock_engine)

    def test_simple_hop_flow(self):
        result = self.rag_graph.run(tenant_id="tenant-dev", query="What is FastAPI?")

        self.assertIsNotNone(result)
        self.assertEqual(result["tenant_id"], "tenant-dev")
        self.assertEqual(result["routing_decision"], "SIMPLE_HOP")
        self.assertTrue(len(result["retrieved_context"]) > 0)
        self.assertIsNotNone(result["draft_answer"])
        self.assertTrue(result["is_grounded"])

    def test_multi_hop_flow(self):
        result = self.rag_graph.run(tenant_id="tenant-dev", query="What is FastAPI and how to deploy?")

        self.assertIsNotNone(result)
        self.assertEqual(result["routing_decision"], "MULTI_HOP")
        self.assertTrue(len(result["sub_queries"]) >= 2)
        self.assertTrue(len(result["retrieved_context"]) > 0)
        self.assertIsNotNone(result["draft_answer"])

    def test_max_iteration_safeguard(self):
        # Setup verifier to always report ungrounded
        self.rag_graph.verifier.__call__ = MagicMock(return_value={"is_grounded": False})
        
        result = self.rag_graph.run(tenant_id="tenant-dev", query="Unmatched question")
        # Ensure graph terminates within max 3 iterations and does not loop infinitely
        self.assertGreaterEqual(result["iteration_count"], 1)
        self.assertLessEqual(result["iteration_count"], 4)


if __name__ == "__main__":
    unittest.main()
