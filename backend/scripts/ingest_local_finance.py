import os
import logging
from dotenv import load_dotenv

from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.parsers.pdf import SECParser
from app.ingestion.embedder import JinaEmbedder
from app.ingestion.storage.vector_store import VectorStoreWrapper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("finance_ingestor")

def ingest_finance(data_dir: str = "data/finance", tenant_id: str = "tenant-fin-default") -> int:
    """
    Ingests SEC Filing HTML documents into Qdrant for the specified tenant.
    """
    if not os.path.exists(data_dir):
        logger.error(f"Finance directory not found: {data_dir}")
        return 0

    logger.info(f"Starting Finance ingestion from '{data_dir}' for tenant '{tenant_id}'...")

    embedder = JinaEmbedder()
    storage = VectorStoreWrapper()
    parser = SECParser()

    pipeline = IngestionPipeline(
        parser=parser,
        embedder=embedder,
        storage=storage,
        tenant_id=tenant_id,
        content_type="finance"
    )

    total_chunks = 0
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".htm") or file.endswith(".html"):
                file_path = os.path.join(root, file)
                logger.info(f"Ingesting SEC filing: {file_path}")
                try:
                    count = pipeline.run(source=file_path)
                    total_chunks += count
                except Exception as e:
                    logger.error(f"Failed to ingest {file_path}: {e}")

    logger.info(f"🎉 Finance ingestion complete! Total chunks stored: {total_chunks}")
    return total_chunks

def main():
    ingest_finance()

if __name__ == "__main__":
    main()
