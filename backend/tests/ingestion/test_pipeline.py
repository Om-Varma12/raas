import logging
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.ingestion.parsers.github import GitHubParser
from backend.app.ingestion.parsers.pdf import SECParser
from backend.app.ingestion.embedder import JinaEmbedder
from backend.app.ingestion.storage.vector_store import VectorStoreWrapper

# Setup basic logging to see the pipeline progress
logging.basicConfig(level=logging.INFO)

def test_devdocs_pipeline():
    print("\n--- Testing DevDocs Ingestion Pipeline ---")
    # Setup components
    parser = GitHubParser()
    embedder = JinaEmbedder(api_key="test_key")
    storage = VectorStoreWrapper()

    pipeline = IngestionPipeline(
        parser=parser,
        embedder=embedder,
        storage=storage,
        tenant_id="tenant-dev-123",
        content_type="devdocs"
    )

    # Mock the API call to avoid 401 Unauthorized
    with patch.object(JinaEmbedder, '_call_api') as mock_api:
        # Return a mock vector for each input text
        mock_api.side_effect = lambda texts, task: [[0.1] * 1024 for _ in texts]

        count = pipeline.run(source="https://github.com/example/repo")
        print(f"DevDocs Pipeline finished. Chunks stored: {count}")

        # Verify isolation/storage
        stored = storage.get_tenant_chunks("tenant-dev-123")
        assert len(stored) == count
        assert stored[0]["payload"]["tenant_id"] == "tenant-dev-123"
        print("✅ DevDocs verification passed!")

def test_finance_pipeline():
    print("\n--- Testing Finance Ingestion Pipeline ---")
    # Setup components
    parser = SECParser()
    embedder = JinaEmbedder(api_key="test_key")
    storage = VectorStoreWrapper()

    pipeline = IngestionPipeline(
        parser=parser,
        embedder=embedder,
        storage=storage,
        tenant_id="tenant-fin-456",
        content_type="finance"
    )

    # Mock the API call
    with patch.object(JinaEmbedder, '_call_api') as mock_api:
        mock_api.side_effect = lambda texts, task: [[0.2] * 1024 for _ in texts]

        count = pipeline.run(source="sec-filing-10k.pdf")
        print(f"Finance Pipeline finished. Chunks stored: {count}")

        # Verify isolation/storage
        stored = storage.get_tenant_chunks("tenant-fin-456")
        assert len(stored) == count
        assert stored[0]["payload"]["tenant_id"] == "tenant-fin-456"
        print("✅ Finance verification passed!")

if __name__ == "__main__":
    try:
        test_devdocs_pipeline()
        test_finance_pipeline()
        print("\n🎉 ALL INGESTION TESTS PASSED!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
