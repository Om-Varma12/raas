from typing import List, Dict, Any
from .base import BaseChunker

class ConversationChunker(BaseChunker):
    """
    Chunker for Support/Issue threads.
    Strategy: Atomic issues for short threads, per-comment for long ones.
    """

    def __init__(self, max_comments_per_chunk: int = 5):
        self.max_comments_per_chunk = max_comments_per_chunk

    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = element["content"]
        metadata = element["metadata"]

        # Simple logic: if content is short enough, keep it atomic
        if len(content.split()) < 500:
            return [{
                "content": content,
                "metadata": {**metadata, "chunk_id": "atomic_conversation"},
                "type": "conversation"
            }]

        # Otherwise, split by "Comment:" markers (introduced by our GitHubParser)
        comments = content.split("Comment:")
        # The first element is usually the Title/Body
        chunks = []

        current_chunk = comments[0]
        comment_count = 0

        for comment in comments[1:]:
            if comment_count >= self.max_comments_per_chunk:
                chunks.append({
                    "content": current_chunk,
                    "metadata": {**metadata, "chunk_index": len(chunks)},
                    "type": "conversation"
                })
                current_chunk = "Comment:" + comment
                comment_count = 1
            else:
                current_chunk += "Comment:" + comment
                comment_count += 1

        chunks.append({
            "content": current_chunk,
            "metadata": {**metadata, "chunk_index": len(chunks)},
            "type": "conversation"
        })

        return chunks
