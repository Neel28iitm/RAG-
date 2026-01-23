
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
# Ensure app_logger is also setup effectively to show logs from ingestion.py
setup_logger('app_logger')

async def main():
    logger.info("🔥 STARTING FORCED RE-INGESTION (V2 Structure) 🔥")
    config = load_config()
    
    # 1. Clear Database
    logger.info("Step 1: Clearing Vector Database...")
    retrieval = RetrievalService(config)
    retrieval.clear()
    
    # 2. Reset Tracking
    logger.info("Step 2: Resetting file tracking (DB)...")
    from src.core.database import get_db, init_db
    from src.core.models import FileTracking
    
    # Init DB (Create Tables)
    init_db()
    
    db = next(get_db())
    try:
        db.query(FileTracking).delete()
        db.commit()
        logger.info("Deleted all tracking records from DB")
    except Exception as e:
        logger.error(f"Failed to clear DB: {e}")
    finally:
        db.close()
    
    # 3. Re-Ingest
    logger.info("Step 3: Queuing Documents for Worker...")
    ingestion = DocumentIngestion(config)
    await ingestion.ingest_documents()
    
    logger.info("✅ Re-Ingestion Tasks Queued! Ensure Celery Worker is running to process them.")
    logger.info("Run: celery -A src.worker.celery_app worker --loglevel=info -P solo")

if __name__ == "__main__":
    asyncio.run(main())
