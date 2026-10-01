import logging
from typing import List, Dict, Any, Optional
try:
    from app.agents.state import AgentState
except ImportError:
    from backend.app.agents.state import AgentState

logger = logging.getLogger(__name__)

class DecomposerAgent:
    """
    Breaks down complex multi-hop queries into smaller, searchable sub-queries.
    """

    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        LangGraph node function.
        Generates a list of sub-queries from the original query.
        """
        query = state["query"]
        logger.info(f"Decomposing query: {query}")

        # In a real implementation, this would be an LLM call.
        # Example: "Break the following complex question into 2-3 simple search queries."

        # Mock implementation: splitting by 'and' or similar keywords
        sub_queries = [query]
        if "and" in query.lower():
            parts = query.lower().split("and")
            sub_queries = [p.strip() for p in parts]

        logger.info(f"Generated sub-queries: {sub_queries}")
        return {"sub_queries": sub_queries}
