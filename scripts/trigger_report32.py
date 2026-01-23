"""
Trigger ingestion for Report 32.pdf
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.ingestion import DocumentIngestion
from src.core.config import load_config

async def main():
    config = load_config()
    ingestor = DocumentIngestion(config)
    
    print("🚀 Triggering ingestion for all files in S3 raw/...")
    print("📝 Report 32.pdf will be queued if found")
    print("-" * 60)
    
    # This will scan S3 and queue any unprocessed files
    await ingestor.ingest_documents()
    
    print("-" * 60)
    print("✅ Ingestion triggered!")
    print("📊 Check worker logs to monitor progress")
    print("")
    print("To check status:")
    print("  python -c \"from src.core.database import get_db; from src.core.models import FileTracking; db = next(get_db()); records = db.query(FileTracking).all(); [print(f'{r.filename}: {r.status}') for r in records]; db.close()\"")

if __name__ == "__main__":
    asyncio.run(main())
