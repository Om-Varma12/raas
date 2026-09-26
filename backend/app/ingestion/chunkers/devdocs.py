from typing import List, Dict, Any
from .base import BaseChunker
import re

class DevDocsChunker(BaseChunker):
    """
    Chunker for DevDocs tenant.
    Strategy: Split by Markdown headers, atomic code blocks.
    """

    def __init__(self, target_tokens: int = 300, overlap: int = 30):
        self.target_tokens = target_tokens
        self.overlap = overlap

    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        content = element["content"]
        metadata = element["metadata"]

        # 1. Handle Fenced Code Blocks as Atomic (TECHNICALS.md)
        # We use a regex to find all code blocks
        code_block_pattern = r"```[\s\S]*?```"

        # If the element is a single code block (indicated by parser or content), return it atomic
        if re.fullmatch(code_block_pattern, content.strip()):
            return [{
                "content": content,
                "metadata": {**metadata, "chunk_id": "atomic_code"},
                "type": "code"
            }]

        # 2. Split by Markdown headers (#, ##, ###)
        # We use a lookahead to split while keeping the header with the content
        sections = re.split(r"\n(?=#\s+)", content)

        chunks = []
        for section in sections:
            # If section is too long, apply recursive splitting
            if len(section.split()) * 1.3 > self.target_tokens:
                # Split by paragraphs within the section
                paragraphs = section.split("\n\n")
                current_chunk = ""

                for para in paragraphs:
                    if (len(current_chunk.split()) * 1.3) + (len(para.split()) * 1.3) > self.target_tokens:
                        if current_chunk:
                            chunks.append(self._create_chunk(current_chunk, metadata))
                            # Overlap
                            words = current_chunk.split()
                            overlap_words = words[-int(self.overlap/1.3):]
                            current_chunk = " ".join(overlap_words) + "\n\n" + para
                        else:
                            current_chunk = para
                    else:
                        current_chunk = (current_chunk + "\n\n" + para).strip()

                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, metadata))
            else:
                chunks.append(self._create_chunk(section, metadata))

        return chunks

    def _create_chunk(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "content": text,
            "metadata": {**metadata},
            "type": "prose"
        }
