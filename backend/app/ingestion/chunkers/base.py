from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseChunker(ABC):
    """
    Abstract base class for all structural chunkers.
    """

    @abstractmethod
    def chunk(self, element: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split the element into smaller chunks.
        Each chunk should be a dictionary containing the content and metadata.
        """
        pass
