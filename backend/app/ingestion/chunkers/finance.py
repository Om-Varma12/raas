from typing import List, Dict, Any
from .base import BaseChunker
import re

class FinanceChunker(BaseChunker):
    """
    Chunker for Finance tenant.
    Strategy: Split by SEC Item sections, then recursive character splitting.
    """

    def __init__(self, target_tokens: int = 500, overlap: int = 50):
        self.target_tokens = target_tokens
        self.overlap = overlap

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

        # Recursive Character Splitting Implementation
        # We split by paragraphs first, then sentences, then words to maintain boundaries.
        chunks = []

        # 1. Split by double newlines (paragraphs)
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            # Approximate token count (1 word ~ 1.3 tokens)
            est_tokens = len(current_chunk.split()) * 1.3

            if est_tokens + (len(para.split()) * 1.3) > self.target_tokens:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, metadata))
                    # Add overlap: take last few words of the previous chunk
                    words = current_chunk.split()
                    overlap_words = words[-int(self.overlap/1.3):]
                    current_chunk = " ".join(overlap_words) + "\n\n" + para
                else:
                    # Paragraph itself is too large, split it further
                    current_chunk = para
            else:
                current_chunk = (current_chunk + "\n\n" + para).strip()

        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, metadata))

        return chunks

    def _create_chunk(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "content": text,
            "metadata": {**metadata},
            "type": "prose"
        }
