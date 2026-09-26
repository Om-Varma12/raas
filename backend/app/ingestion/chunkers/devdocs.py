from typing import List, Dict, Any
from .base import BaseChunker
import re

class DevDocsChunker(BaseChunker):
    """
    Chunker for DevDocs tenant.
    Strategy: Split by Markdown headers, atomic code blocks.
    """

    def __init__(self, target_tokens: int = 300):
        self.target_tokens = target_tokens

    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = element["content"]
        metadata = element["metadata"]

        # 1. Handle Fenced Code Blocks as Atomic (TECHNICALS.md)
        code_blocks = re.findall(r"```[\s\S]*?```", content)
        if code_blocks:
            # If the element is primarily a code block, keep it atomic
            # otherwise, we handle it during prose splitting
            if len(code_blocks[0]) / len(content) > 0.8:
                return [{
                    "content": content,
                    "metadata": {**metadata, "chunk_id": "atomic_code"},
                    "type": "code"
                }]

        # 2. Handle Markdown Header Splitting
        # Split by #, ##, ###
        sections = re.split(r"\n(?=#\s+)", content)

        chunks = []
        for i, section in enumerate(sections):
            # If section is too long, do a simple split
            if len(section.split()) > self.target_tokens:
                words = section.split()
                for j in range(0, len(words), self.target_tokens):
                    chunks.append({
                        "content": " ".join(words[j : j + self.target_tokens]),
                        "metadata": {**metadata, "chunk_index": f"{i}_{j}"},
                        "type": "prose"
                    })
            else:
                chunks.append({
                    "content": section,
                    "metadata": {**metadata, "chunk_index": i},
                    "type": "prose"
                })

        return chunks
