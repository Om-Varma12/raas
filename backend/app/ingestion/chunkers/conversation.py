from typing import List, Dict, Any
from .base import BaseChunker

class ConversationChunker(BaseChunker):
    """
    Chunker for Support/Issue threads.
    Strategy: Atomic issues for short threads, per-comment for long ones.
    """

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens

    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = element["content"]
        metadata = element["metadata"]

        # As per TECHNICALS.md: GitHub issues use a separate strategy
        # If the whole issue is short, keep it atomic.
        if len(content.split()) * 1.3 < self.max_tokens:
            return [{
                "content": content,
                "metadata": {**metadata, "chunk_id": "atomic_conversation"},
                "type": "conversation"
            }]

        # Otherwise, split by the "Comment:" markers produced by the parser.
        # We want to keep the Title/Body in the first chunk.
        parts = content.split("Comment:")

        chunks = []
        current_chunk = parts[0].strip()

        for i in range(1, len(parts)):
            comment = "Comment:" + parts[i]
            # Check if adding this comment exceeds the token limit
            if (len(current_chunk.split()) * 1.3) + (len(comment.split()) * 1.3) > self.max_tokens:
                chunks.append({
                    "content": current_chunk,
                    "metadata": {**metadata, "chunk_index": len(chunks)},
                    "type": "conversation"
                })
                current_chunk = comment
            else:
                current_chunk += "\n" + comment

        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "metadata": {**metadata, "chunk_index": len(chunks)},
                "type": "conversation"
            })

        return chunks
