import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.core.database import init_db
from datetime import datetime

# Initialize DB
init_db()

async def trigger_ingestion():
    print(f"DEBUG: Trigger Time (UTC): {datetime.utcnow()}")
    config = load_config("config/settings.yaml")
    ingestor = DocumentIngestion(config)
    
    # DEBUG KEYS
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    print(f"DEBUG: AK={'found' if ak else 'MISSING'} SK={'found' if sk else 'MISSING'}")
    if sk: print(f"DEBUG: SK Start: {sk[:2]}") # Check if + is preserved

    print("Triggering S3 Ingestion Scan...")
    await ingestor.ingest_documents()
    print("Scan Complete.")

if __name__ == "__main__":
    asyncio.run(trigger_ingestion())
