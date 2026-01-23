import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv('config/.env')

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.core.database import get_db
from src.core.models import FileTracking
from src.app.retrieval import RetrievalService

async def main():
    filename = "Report no 32.pdf"
    file_key = f"raw/{filename}"
    
    print(f"🗑️ Step 1: Deleting old chunks for {filename}...")
    config = load_config()
    retriever = RetrievalService(config)
    retriever.delete_documents_by_source(filename)
    print("✅ Old chunks deleted")
    
    print(f"🗑️ Step 2: Deleting DB record...")
    db = next(get_db())
    record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
    if record:
        db.delete(record)
        db.commit()
        print("✅ DB record deleted")
    db.close()
    
    print(f"🚀 Step 3: Re-ingesting with Vision Enhancement...")
    ingester = DocumentIngestion(config)
    chunks = await ingester.process_file(file_key, check_processed=False)
    
    print(f"✅ Generated {len(chunks)} chunks")
    
    print(f"📥 Step 4: Indexing to Qdrant...")
    retriever.add_documents(chunks)
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())
