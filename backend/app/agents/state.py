from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """
    State object for the LangGraph agentic RAG flow.
    Tracks the lifecycle of a query from routing to verification.
    """
    tenant_id: str
    query: str
    sub_queries: List[str]
    retrieved_context: List[dict]
    draft_answer: Optional[str]
    is_grounded: Optional[bool]
    routing_decision: Optional[str]
    iteration_count: int
