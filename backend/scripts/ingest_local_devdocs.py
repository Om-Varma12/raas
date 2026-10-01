import os
import logging
from dotenv import load_dotenv

from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.parsers.github import GitHubParser
from app.ingestion.embedder import JinaEmbedder
from app.ingestion.storage.vector_store import VectorStoreWrapper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("devdocs_ingestor")

def ingest_devdocs(data_dir: str = "data/devdocs", tenant_id: str = "tenant-dev-default") -> int:
    """
    Ingests DevDocs (Markdown files & GitHub issues) into Qdrant for the specified tenant.
    """
    if not os.path.exists(data_dir):
        logger.error(f"DevDocs directory not found: {data_dir}")
        return 0

    logger.info(f"Starting DevDocs ingestion from '{data_dir}' for tenant '{tenant_id}'...")

    embedder = JinaEmbedder()
    storage = VectorStoreWrapper()
    parser = GitHubParser()

    pipeline = IngestionPipeline(
        parser=parser,
        embedder=embedder,
        storage=storage,
        tenant_id=tenant_id,
        content_type="devdocs"
    )

    total_chunks = pipeline.run(source=data_dir)
    logger.info(f"🎉 DevDocs ingestion complete! Total chunks stored: {total_chunks}")
    return total_chunks

def main():
    ingest_devdocs()

if __name__ == "__main__":
    main()
