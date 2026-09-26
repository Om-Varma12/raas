from enum import Enum
from typing import List, Dict, Any
import re

class ContentType(Enum):
    PROSE = "prose"
    TABLE = "table"
    CODE = "code"
    CONVERSATION = "conversation"

class ContentTypeDetector:
    """
    Detects the content type of a parsed element to route it
    to the correct structural chunker.
    """

    def detect(self, element: Dict[str, Any]) -> ContentType:
        # 1. Priority: Explicit hint from parser
        hint = element.get("type")
        if hint == "table":
            return ContentType.TABLE
        if hint == "conversation":
            return ContentType.CONVERSATION
        if hint == "markdown":
            # Markdown can be prose or code, let's analyze content
            return self._analyze_markdown(element["content"])
        if hint == "prose":
            return ContentType.PROSE

        # 2. Fallback: Heuristic analysis of content
        return self._analyze_content(element["content"])

    def _analyze_markdown(self, content: str) -> ContentType:
        # If it's mostly fenced code blocks
        code_block_pattern = r"```[\s\S]*?```"
        code_blocks = re.findall(code_block_pattern, content)

        if len(code_blocks) > 0:
            # Simple heuristic: if > 50% of content is code, mark as CODE
            code_len = sum(len(b) for b in code_blocks)
            if code_len / len(content) > 0.5:
                return ContentType.CODE

        return ContentType.PROSE

    def _analyze_content(self, content: str) -> ContentType:
        # Detect Tables: Look for markdown pipes or TSV/CSV patterns
        if content.count("|") > 3 and ("---" in content or "\n" in content):
            return ContentType.TABLE

        # Detect Conversations: Look for "User:", "Bot:", or "Comment:" patterns
        conv_patterns = [r"User:", r"Bot:", r"Comment:", r"Author:"]
        if any(re.search(p, content) for p in conv_patterns):
            return ContentType.CONVERSATION

        # Detect Code: Look for common keywords (def, function, const, let, class)
        code_keywords = [r"\bdef\b", r"\bfunction\b", r"\bconst\b", r"\blet\b", r"\bclass\b"]
        if any(re.search(p, content) for p in code_keywords):
            return ContentType.CODE

        return ContentType.PROSE
