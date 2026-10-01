import os
from typing import List, Dict, Any
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
from .base import BaseParser

class SECParser(BaseParser):
    """
    Parser for SEC filings (10-K, 10-Q).
    Actual implementation: Parses .htm files and extracts structural items and tables.
    """

    def parse(self, source: str) -> List[Dict[str, Any]]:
        """
        source: Path to the .htm filing file.
        """
        if not os.path.exists(source):
            raise FileNotFoundError(f"SEC filing not found at: {source}")

        with open(source, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')
        elements = []

        # 1. Extract Tables (TECHNICALS.md: Tables are separate retrieval units)
        # We look for <table> tags. In SEC filings, these are often critical.
        for table in soup.find_all('table'):
            # Convert table to markdown-like format for embedding
            table_text = self._table_to_text(table)
            elements.append({
                "content": table_text,
                "metadata": {
                    "source_type": "filing_table",
                    "doc_path": source,
                    "item_number": self._find_nearest_item(table, soup)
                },
                "type": "table"
            })

        # 2. Extract Structural Sections (Items)
        # SEC filings use patterns like "Item 1.", "Item 1A.", etc.
        # We look for headers or bold text that match this pattern.
        text_content = soup.get_text(separator='\n')

        # Regex-like split on "Item [Number]"
        import re
        # Matches "Item 1", "Item 1A", etc., usually at start of line or after newline
        item_pattern = r"(?m)^Item\s+([0-9][A-Z]?)\.?\s+"
        matches = list(re.finditer(item_pattern, text_content))

        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text_content)

            item_num = matches[i].group(1)
            section_content = text_content[start:end].strip()

            elements.append({
                "content": section_content,
                "metadata": {
                    "source_type": "filing_section",
                    "doc_path": source,
                    "item_number": f"Item {item_num}"
                },
                "type": "prose"
            })

        return elements

    def _table_to_text(self, table) -> str:
        """Converts a BeautifulSoup table object to a simplified text representation."""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join(rows)

    def _find_nearest_item(self, element, soup) -> str:
        """Attempts to find which 'Item' section a table belongs to by looking backwards."""
        # This is a heuristic: look at preceding text for the nearest 'Item X' pattern
        # In a real complex implementation, we would use the DOM tree.
        return "Unknown Item" # Simplified for now
