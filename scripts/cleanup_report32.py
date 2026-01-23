import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv('config/.env')

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.core.database import get_db
from src.core.models import FileTracking

async def main():
    filename = "Report no 32.pdf"
    
    print(f"🗑️ Deleting chunks for {filename}...")
    config = load_config()
    retriever = RetrievalService(config)
    retriever.delete_documents_by_source(filename)
    print("✅ Chunks deleted")
    
    print(f"🗑️ Deleting DB record...")
    db = next(get_db())
    record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
    if record:
        db.delete(record)
        db.commit()
        print("✅ DB record deleted")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())
