
import asyncio
import os
import sys
import yaml
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger
from src.app.retrieval import RetrievalService
from src.app.ingestion import DocumentIngestion
from src.core.config import load_config

# Load Env
load_dotenv("config/.env")
logger = setup_logger('reingest_logger')

async def main():
    logger.info("🔥 STARTING FORCED RE-INGESTION (V2 Structure) 🔥")
    config = load_config()
    
    # 1. Clear Database
    logger.info("Step 1: Clearing Vector Database...")
    retrieval = RetrievalService(config)
    retrieval.clear()
    
    # 2. Reset Tracking
    logger.info("Step 2: Resetting file tracking...")
    tracking_file = config['paths']['tracking_file']
    if os.path.exists(tracking_file):
        os.remove(tracking_file)
        logger.info(f"Deleted {tracking_file}")
    
    # 3. Re-Ingest
    logger.info("Step 3: Ingesting Documents with NEW Embeddings...")
    ingestion = DocumentIngestion(config)
    chunks = await ingestion.ingest_documents()
    
    if chunks:
        logger.info(f"Step 4: Adding {len(chunks)} chunks to Qdrant...")
        retrieval.add_documents(chunks)
        logger.info("✅ Re-Ingestion Complete!")
    else:
        logger.warning("⚠️ No documents found to ingest.")

if __name__ == "__main__":
    asyncio.run(main())
