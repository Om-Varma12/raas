import os
from typing import List, Dict, Any
from .base import BaseParser

class GitHubParser(BaseParser):
    """
    Parser for GitHub repositories, handling both Markdown documentation
    and GitHub Issue threads.
    """

    def parse(self, source: Any) -> List[Dict[str, Any]]:
        # In a real implementation, 'source' would be a path to a local
        # cloned repo or a GitHub API response.

        elements = []

        # Mock logic for GitHub Docs (.md files)
        # In reality, this would walk the directory and read .md files
        mock_md_content = "# Installation\nRun pip install raas\n\n## Configuration\nSet the API key in .env"
        elements.append({
            "content": mock_md_content,
            "metadata": {"source_type": "md_doc", "path": "docs/install.md"},
            "type": "markdown"
        })

        # Mock logic for GitHub Issues
        mock_issue = {
            "title": "Bug: Retrieval too slow",
            "body": "I noticed the p95 latency is above 4s.",
            "comments": ["I'll look into the HNSW config.", "Fixed it by increasing ef_search."]
        }

        # We represent an issue as a single unit if short,
        # or separate comments if long.
        issue_content = f"Title: {mock_issue['title']}\nBody: {mock_issue['body']}\n"
        issue_content += "\n".join([f"Comment: {c}" for c in mock_issue['comments']])

        elements.append({
            "content": issue_content,
            "metadata": {"source_type": "issue_thread", "issue_number": 123},
            "type": "conversation"
        })

        return elements
