
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.core.database import get_db
from src.core.models import FileTracking
from datetime import datetime
from dotenv import load_dotenv

# Load env variables
env_path = Path('config/.env')
if not env_path.exists():
    env_path = Path('.env')

print(f"📂 Loading env from: {env_path.absolute()}")
load_dotenv(env_path)

# Debug Keys
aws_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
print(f"🔑 AWS_ACCESS_KEY_ID: {'✅ SET' if aws_key else '❌ MISSING'}")
print(f"🔑 AWS_SECRET_ACCESS_KEY: {'✅ SET' if aws_secret else '❌ MISSING'}")
print(f"🪣 S3_BUCKET_NAME: {os.getenv('S3_BUCKET_NAME')}")

if not aws_key or not aws_secret:
    print("❌ CRITICAL: AWS Credentials missing! Cannot proceed.")
    sys.exit(1)

async def main():
    filename = "Report no 32.pdf"
    file_key = f"raw/{filename}"
    
    print(f"🚀 Starting manual ingestion for: {filename}")
    
    # 1. Update DB Status to PROCESSING
    db = next(get_db())
    record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
    if record:
        record.status = "PROCESSING"
        record.started_at = datetime.utcnow()
        record.error_msg = None
        db.commit()
        print("✅ DB Status updated to PROCESSING")
    else:
        print("⚠️ Record not found in DB!")
    db.close()

    try:
        # 2. Initialize Ingestion
        config = load_config()
        ingester = DocumentIngestion(config)
        
        # 3. Process File (Direct call)
        # Note: process_file expects local path usually, or S3 key if modified?
        # Looking at ingestion.py: process_file takes 'file_path'
        # Inside it acts as S3 Key: s3_key = str(file_path).replace("\\", "/")
        # So we pass the S3 Key directly.
        
        print("⏳ Processing started (Gemini 2.5 Flash Multimodal)...")
        chunks = await ingester.process_file(file_key, check_processed=False)
        
        print(f"✅ Processing Complete! Generated {len(chunks)} chunks.")
        
        # 4. Indexing (Critical Step)
        if chunks:
            from src.app.retrieval import RetrievalService
            print("🔄 Initializing Retrieval Service for Indexing...")
            retriever = RetrievalService(config)
            
            # Delete old vectors
            print(f"🗑️ Deleting old vectors for {filename}...")
            retriever.delete_documents_by_source(filename)
            
            # Add new vectors
            print(f"📥 Indexing {len(chunks)} chunks to Qdrant...")
            retriever.add_documents(chunks)
            print("✅ Indexing Complete!")
        
        # 5. Success Status
        db = next(get_db())
        record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        record.status = "COMPLETED"
        record.completed_at = datetime.utcnow()
        db.commit()
        print("✅ DB Status updated to COMPLETED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db = next(get_db())
        record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        record.status = "FAILED"
        record.error_msg = str(e)
        db.commit()
        db.close()
        raise e
    finally:
        if 'db' in locals(): db.close()

if __name__ == "__main__":
    asyncio.run(main())
