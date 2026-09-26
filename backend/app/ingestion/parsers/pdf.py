from typing import List, Dict, Any
from .base import BaseParser

class SECParser(BaseParser):
    """
    Parser for SEC filings (10-K, 10-Q).
    Focuses on separating structural sections (Items) and extracting tables.
    """

    def parse(self, source: Any) -> List[Dict[str, Any]]:
        # In a real implementation, this would use BeautifulSoup or 'unstructured'
        # to parse the .htm or PDF files.

        elements = []

        # SEC section splitting (Item 1, Item 7, etc.)
        mock_sections = [
            {"item": "Item 1", "content": "The company operates in the AI space..."},
            {"item": "Item 7", "content": "Management's discussion on revenue..."},
        ]

        for section in mock_sections:
            elements.append({
                "content": section["content"],
                "metadata": {"item_number": section["item"], "source_type": "filing_section"},
                "type": "prose"
            })

        mock_table = "| Year | Revenue |\n| 2023 | $10M |\n| 2022 | $8M |"
        elements.append({
            "content": mock_table,
            "metadata": {"item_number": "Item 7", "source_type": "filing_table"},
            "type": "table"
        })

        return elements
