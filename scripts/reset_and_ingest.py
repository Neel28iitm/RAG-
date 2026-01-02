
import sys
import os
import asyncio
import yaml
from dotenv import load_dotenv

# Project root add karo path mein
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from src.core.database import Base, engine

load_dotenv("config/.env")
logger = setup_logger('migration_logger')

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

async def main():
    config = load_config()
    
    # 1. Clear SQLite DB (Sessions)
    logger.info("🗑️  Clearing Chat History DB...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 2. Ingest Documents
    logger.info("🚀 Starting Ingestion Process...")
    ingestion = DocumentIngestion(config)
    
    # Force re-ingestion by clearing tracking file logic or just let ingestion handle it?
    # Since we changed schema, we WANT to re-process. 
    # DocumentIngestion uses tracking file. We should delete it first to ensure it runs.
    tracking_file = config['paths']['tracking_file']
    if os.path.exists(tracking_file):
        os.remove(tracking_file)
        logger.info("Removed tracking file to force re-ingest.")
        # Re-init ingestion to reset memory state
        ingestion = DocumentIngestion(config)

    chunks = await ingestion.ingest_documents() 
    
    # 3. Index to Qdrant (Hybrid)
    if chunks:
        logger.info(f"🧩 Found {len(chunks)} chunks. Indexing to Vector DB...")
        # Lazy creation logic inside RetrievalService handles missing collection
        # But for optimization/schema change, we want to start fresh to avoid duplicates
        # We can't rely on RetrievalService(force_create=True) as we had issues with it earlier.
        # So manual cleanup via raw client before init:
        try:
             # Basic client to delete collection
            from src.core.vector_store import get_qdrant_client
            temp_client = get_qdrant_client(config)
            temp_client.delete_collection(config['paths']['vector_store_config']['collection_name'])
            logger.info("🗑️  Old Qdrant collection deleted (Clean Start).")

            # EXPLICITLY RECREATE WITH HYBRID SCHEMA
            # We must ensure the collection has the sparse vector config before adding docs
            from qdrant_client import models
            temp_client.create_collection(
                collection_name=config['paths']['vector_store_config']['collection_name'],
                vectors_config=models.VectorParams(
                    size=768, 
                    distance=models.Distance.COSINE
                ),
                sparse_vectors_config={
                    "langchain-sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        )
                    )
                },
                on_disk_payload=True
            )
            logger.info("✅ Re-created Collection with Hybrid Schema.")

        except Exception as e:
            logger.warning(f"⚠️ Collection reset/creation warning: {e}")

        retrieval = RetrievalService(config)
        
        # We don't need manual delete anymore as QdrantVectorStore handles it with force_recreate=True
        # Naye documents add karo (Dense + Sparse auto-generate honge)
        retrieval.add_documents(chunks)
        logger.info("🎉 Migration & Ingestion Complete!")
    else:
        logger.warning("⚠️  No documents found to ingest.")

if __name__ == "__main__":
    asyncio.run(main())
