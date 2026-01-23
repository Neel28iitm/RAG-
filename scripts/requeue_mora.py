
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.core.database import get_db, init_db
from src.core.models import FileTracking
from src.app.ingestion import DocumentIngestion

load_dotenv("config/.env")
load_dotenv(".env")

async def main():
    print("------- RE-QUEUING MORA -------")
    config = load_config()
    filename = "25016_FME - Utomhusfläkt_Mora.pdf"
    
    # 1. Clear DB Status
    db = next(get_db())
    try:
        record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        if record:
            print(f"Found record: {record.status}. Deleting...")
            db.delete(record)
            db.commit()
            print("Deleted record from DB.")
        else:
            print("Record not found in DB.")
    except Exception as e:
        print(f"Error accessing DB: {e}")
    finally:
        db.close()

    # 2. Trigger Ingestion (Queue)
    # The IngestDocuments method scans S3 and queues if not in DB.
    # Since we deleted it, it should queue it.
    print("Triggering Ingestion Scan...")
    ingestion = DocumentIngestion(config)
    await ingestion.ingest_documents()
    print("✅ Ingestion triggered. Check Worker logs.")

if __name__ == "__main__":
    asyncio.run(main())
