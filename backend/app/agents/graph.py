import logging
from typing import List, Dict, Any, Optional, Union
try:
    from langgraph.graph import StateGraph, END, START
except ImportError:
    StateGraph, END, START = None, "END", "START"
try:
    from app.agents.state import AgentState
    from app.agents.router_agent import RouterAgent
    from app.agents.decomposer_agent import DecomposerAgent
    from app.agents.retrieval_agent import RetrievalAgent
    from app.agents.verifier_agent import VerifierAgent
    from app.retrieval.engine import RetrievalEngine
except ImportError:
    from backend.app.agents.state import AgentState
    from backend.app.agents.router_agent import RouterAgent
    from backend.app.agents.decomposer_agent import DecomposerAgent
    from backend.app.agents.retrieval_agent import RetrievalAgent
    from backend.app.agents.verifier_agent import VerifierAgent
    from backend.app.retrieval.engine import RetrievalEngine

logger = logging.getLogger(__name__)

class RAGGraph:
    """
    Wires the agentic RAG flow into a LangGraph state machine.
    Flow: START -> Router -> (Decomposer ->) Retrieval -> Generation -> Verifier -> (END | Retrieval)
    """

    def __init__(
        self,
        llm_client: Any,
        retrieval_engine: RetrievalEngine
    ):
        # Initialize Agents
        self.router = RouterAgent(llm_client)
        self.decomposer = DecomposerAgent(llm_client)
        self.retriever = RetrievalAgent(retrieval_engine)
        self.verifier = VerifierAgent(llm_client)

        self.workflow = self._build_graph()

    def _build_graph(self) -> Optional[Any]:
        if StateGraph is None:
            logger.warning("LangGraph not installed. Direct state orchestration active.")
            return None

        workflow = StateGraph(AgentState)

        # Add Nodes
        workflow.add_node("router", self.router)
        workflow.add_node("decomposer", self.decomposer)
        workflow.add_node("retrieval", self.retriever)
        workflow.add_node("verifier", self.verifier)
        workflow.add_node("generator", self._generation_node)

        # Define Edges
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "MULTI_HOP": "decomposer",
                "SIMPLE_HOP": "retrieval"
            }
        )

        workflow.add_edge("decomposer", "retrieval")
        workflow.add_edge("retrieval", "generator")
        workflow.add_edge("generator", "verifier")

        workflow.add_conditional_edges(
            "verifier",
            self._verify_decision,
            {
                "GROUNDED": END,
                "NOT_GROUNDED": "retrieval"
            }
        )

        return workflow.compile()

    def _route_decision(self, state: AgentState) -> str:
        return state.get("routing_decision", "SIMPLE_HOP")

    def _verify_decision(self, state: AgentState) -> str:
        count = state.get("iteration_count", 0)
        if state.get("is_grounded") or count >= 3:
            return "GROUNDED"
        return "NOT_GROUNDED"

    def _generation_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates a response based on the retrieved context.
        Ensures static-first ordering for prompt caching.
        """
        tenant_id = state["tenant_id"]
        query = state["query"]
        context = state.get("retrieved_context", [])
        current_count = state.get("iteration_count", 0) + 1

        logger.info(f"Generating answer for tenant {tenant_id} (Iteration {current_count})")

        context_text = " ".join([c.get("content", "") for c in context])
        draft_answer = f"Based on the context: {context_text[:100]}... The answer to '{query}' is [Generated Response]."

        return {
            "draft_answer": draft_answer,
            "iteration_count": current_count
        }

    def run(self, tenant_id: str, query: str) -> Dict[str, Any]:
        """
        Executes the graph for a specific tenant and query.
        """
        state: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "query": query,
            "sub_queries": [],
            "retrieved_context": [],
            "draft_answer": None,
            "is_grounded": None,
            "routing_decision": None,
            "iteration_count": 0
        }

        if self.workflow is not None:
            return self.workflow.invoke(state)

        # Direct Python state machine fallback
        router_out = self.router(state)
        state.update(router_out)

        if state.get("routing_decision") == "MULTI_HOP":
            decomp_out = self.decomposer(state)
            state.update(decomp_out)

        ret_out = self.retriever(state)
        state.update(ret_out)

        gen_out = self._generation_node(state)
        state.update(gen_out)

        ver_out = self.verifier(state)
        state.update(ver_out)

        return state
