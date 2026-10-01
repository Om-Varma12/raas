import logging
from typing import List, Dict, Any, Optional
from backend.app.agents.state import AgentState

logger = logging.getLogger(__name__)

class VerifierAgent:
    """
    Checks if the generated answer is grounded in the retrieved context.
    """

    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        LangGraph node function.
        Validates the draft answer against the retrieved context.
        """
        answer = state.get("draft_answer")
        context = state.get("retrieved_context", [])

        if not answer or not context:
            logger.warning("Verification skipped: missing answer or context.")
            return {"is_grounded": False}

        logger.info("Verifying answer grounding...")

        # In a real implementation, this would be an LLM call.
        # Prompt: "Does the following answer derive solely from the provided context? Answer YES or NO."

        # Mock implementation: check if any key words from answer are in the context
        context_text = " ".join([c.get("content", "") for c in context])
        # Very simple mock grounding check
        is_grounded = any(word in context_text.lower() for word in answer.lower().split() if len(word) > 5)

        logger.info(f"Grounding check result: {is_grounded}")
        return {"is_grounded": is_grounded}
