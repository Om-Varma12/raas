from typing import List, Dict, Any
from .base import BaseChunker
import re

class FinanceChunker(BaseChunker):
    """
    Chunker for Finance tenant.
    Strategy: Split by SEC Item sections, then recursive character splitting.
    """

    def __init__(self, target_tokens: int = 500):
        self.target_tokens = target_tokens

    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = element["content"]
        metadata = element["metadata"]

        # As per TECHNICALS.md: Tables are atomic retrieval units
        if metadata.get("source_type") == "filing_table":
            return [{
                "content": content,
                "metadata": {**metadata, "chunk_id": "atomic_table"},
                "type": "table"
            }]

        # For prose, we assume the parser already split by SEC Item.
        # We now do a simple size-based split if it's still too long.
        chunks = []
        words = content.split()

        # Rough token estimation (1 word approx 1.3 tokens)
        for i in range(0, len(words), int(self.target_tokens / 1.3)):
            chunk_content = " ".join(words[i : i + int(self.target_tokens / 1.3)])
            chunks.append({
                "content": chunk_content,
                "metadata": {**metadata, "chunk_index": i // int(self.target_tokens / 1.3)},
                "type": "prose"
            })

        return chunks
