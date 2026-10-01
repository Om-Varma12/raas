import logging
from dotenv import load_dotenv
from scripts.ingest_local_devdocs import ingest_devdocs
from scripts.ingest_local_finance import ingest_finance

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("all_data_ingestor")

def main():
    logger.info("🚀 Starting ingestion for ALL local datasets...")
    
    devdocs_chunks = ingest_devdocs()
    finance_chunks = ingest_finance()
    
    total = devdocs_chunks + finance_chunks
    logger.info(f"✨ ALL LOCAL DATA INGESTED! Total chunks in Qdrant: {total}")

if __name__ == "__main__":
    main()
