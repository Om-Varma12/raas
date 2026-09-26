import os
from typing import List, Dict, Any
from .base import BaseParser

class GitHubParser(BaseParser):
    """
    Parser for GitHub repositories.
    Actual implementation: Reads local markdown files and mock-simulates API data.
    """

    def parse(self, source: str) -> List[Dict[str, Any]]:
        """
        source: Path to the local cloned repository directory.
        """
        if not os.path.isdir(source):
            raise NotADirectoryError(f"GitHub repo path not found: {source}")

        elements = []

        # 1. Parse Markdown Documentation
        for root, _, files in os.walk(source):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    elements.append({
                        "content": content,
                        "metadata": {
                            "source_type": "md_section",
                            "doc_path": os.path.relpath(file_path, source)
                        },
                        "type": "markdown"
                    })

        # 2. Handle GitHub Issues
        # In a real production setup, this would call the GitHub REST API.
        # To keep the code runnable without API keys for now, we'll check for a
        # 'issues.json' file in the repo root as a data source.
        issues_file = os.path.join(source, "issues.json")
        if os.path.exists(issues_file):
            import json
            with open(issues_file, 'r', encoding='utf-8') as f:
                issues_data = json.load(f)
                for issue in issues_data:
                    # As per TECHNICALS.md: Title + Body + accepted comment
                    content = f"Title: {issue['title']}\nBody: {issue['body']}\n"
                    if "comments" in issue:
                        content += "\n".join([f"Comment: {c}" for c in issue['comments']])

                    elements.append({
                        "content": content,
                        "metadata": {
                            "source_type": "issue_thread",
                            "issue_number": issue.get("number"),
                            "repo_name": os.path.basename(source)
                        },
                        "type": "conversation"
                    })

        return elements
