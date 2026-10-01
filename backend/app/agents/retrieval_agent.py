import logging
from typing import List, Dict, Any, Optional
from backend.app.agents.state import AgentState
from backend.app.retrieval.engine import RetrievalEngine

logger = logging.getLogger(__name__)

class RetrievalAgent:
    """
    Agent responsible for executing retrieval using the RetrievalEngine.
    Aggregates context from one or more queries.
    """

    def __init__(self, engine: RetrievalEngine):
        self.engine = engine

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        LangGraph node function.
        Retrieves context for all active queries in the state.
        """
        tenant_id = state["tenant_id"]
        # Use decomposed sub_queries if available, otherwise use the main query
        queries_to_run = state.get("sub_queries") or [state["query"]]

        logger.info(f"Agent retrieving for tenant {tenant_id} with {len(queries_to_run)} queries.")

        all_context = []
        for q in queries_to_run:
            chunks = self.engine.retrieve(tenant_id=tenant_id, query=q)
            all_context.extend(chunks)

        # Deduplicate chunks by content hash if present
        seen_hashes = set()
        unique_context = []
        for chunk in all_context:
            h = chunk.get("content_hash")
            if h and h not in seen_hashes:
                unique_context.append(chunk)
                seen_hashes.add(h)
            elif not h:
                unique_context.append(chunk)

        return {
            "retrieved_context": unique_context
        }
