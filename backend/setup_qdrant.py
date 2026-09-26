import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

def main():
    # Initialize client
    client = QdrantClient("localhost", port=6333)

    # Tenant config from SCHEMA.md
    tenants = {
        "finance": {
            "id": "001",
            "ef_construct": 200,
        },
        "devdocs": {
            "id": "002",
            "ef_construct": 150,
        }
    }

    for tenant_type, config in tenants.items():
        tenant_id = config["id"]
        collection_name = f"tenant_{tenant_id}"
        
        print(f"Processing collection {collection_name} ({tenant_type})...")
        
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=2048, 
                    distance=models.Distance.COSINE
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(),
            },
            hnsw_config=models.HnswConfigDiff(
                ef_construct=config["ef_construct"],
            ),
        )
        
        # Payload Indexes
        shared_indexed = ["tenant_id", "doc_id", "content_hash", "source_type"]
        if tenant_type == "finance":
            specific_indexed = ["fiscal_period", "filing_date", "item_number", "company_ticker"]
        elif tenant_type == "devdocs":
            specific_indexed = ["repo_name", "issue_number"]
        else:
            specific_indexed = []

        for field in (shared_indexed + specific_indexed):
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            
        print(f"Successfully initialized {collection_name}")

if __name__ == "__main__":
    main()
