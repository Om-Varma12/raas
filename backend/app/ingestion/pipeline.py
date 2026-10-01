from typing import List, Dict, Any, Optional
import logging

from .parsers.base import BaseParser
from .content_type import ContentTypeDetector, ContentType
from .chunkers.base import BaseChunker
from .chunkers.finance import FinanceChunker
from .chunkers.devdocs import DevDocsChunker
from .chunkers.conversation import ConversationChunker
from .embedder import JinaEmbedder
from .storage.vector_store import VectorStoreWrapper

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Orchestrates the full ingestion flow:
    Parse -> Detect -> Chunk -> Embed -> Store.
    """

    def __init__(
        self,
        parser: BaseParser,
        embedder: JinaEmbedder,
        storage: VectorStoreWrapper,
        tenant_id: str,
        content_type: str # "finance" | "devdocs"
    ):
        self.parser = parser
        self.embedder = embedder
        self.storage = storage
        self.tenant_id = tenant_id
        self.content_type = content_type
        self.detector = ContentTypeDetector()

        # Select the appropriate chunker based on tenant content_type
        self.chunker = self._get_chunker_for_tenant()

    def _get_chunker_for_tenant(self) -> BaseChunker:
        if self.content_type == "finance":
            return FinanceChunker()
        elif self.content_type == "devdocs":
            return DevDocsChunker()
        else:
            # Default to conversation or generic
            return ConversationChunker()

    def run(self, source: Any):
        """
        Executes the ingestion pipeline on the provided source.
        """
        logger.info(f"Starting ingestion for tenant {self.tenant_id} ({self.content_type})")

        # 1. Parse: Raw Source -> Elements
        elements = self.parser.parse(source)
        logger.info(f"Parsed {len(elements)} elements.")

        all_chunks = []

        for element in elements:
            # 2. Detect: Element -> ContentType
            c_type = self.detector.detect(element)

            # 3. Chunk: Element -> Chunks (based on detected type)
            # Note: We use the tenant-specific chunker, but it can internalize
            # the c_type logic (e.g. FinanceChunker handles tables differently).
            chunks = self.chunker.chunk(element)
            all_chunks.extend(chunks)

        logger.info(f"Generated {len(all_chunks)} chunks.")

        # 4. Embed: Chunks -> Vectors
        # Batch embed all chunk contents for efficiency
        texts_to_embed = [c["content"] for c in all_chunks]
        vectors = self.embedder.embed(texts_to_embed, task="retrieval.passage")

        # Attach vectors to chunks
        for i, chunk in enumerate(all_chunks):
            chunk["vector"] = vectors[i]

        # 5. Store: Chunks -> Vector Store
        self.storage.store_chunks(
            collection_name=self.tenant_id,
            chunks=all_chunks,
            tenant_id=self.tenant_id
        )
        logger.info(f"Successfully stored {len(all_chunks)} chunks for tenant {self.tenant_id}.")

        return len(all_chunks)
