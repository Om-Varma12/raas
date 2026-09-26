from abc import ABC, abstractmethod
from typing import Any, List, Dict

class BaseParser(ABC):
    """
    Abstract base class for all document parsers.
    Parsers should return a list of elements, where each element
    is a dictionary containing the content and metadata.
    """

    @abstractmethod
    def parse(self, source: Any) -> List[Dict[str, Any]]:
        """
        Parse the source and return a list of parsed elements.

        Each element should follow this structure:
        {
            "content": str,
            "metadata": Dict[str, Any],
            "type": str # Hint for the content detector
        }
        """
        pass
