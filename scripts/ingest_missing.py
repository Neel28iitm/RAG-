"""
Script: scripts/ingest_missing.py
Purpose: Ingest specific missing files without wiping the system.
Usage: python scripts/ingest_missing.py
"""

import sys
import os
import asyncio
import logging
import boto3
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.config import load_config
from src.core.database import SessionLocal
from src.core.models import FileTracking
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ingest_missing')

async def ingest_file(filename):
    load_dotenv()
    config = load_config()
    ingestion = DocumentIngestion(config)
    retrieval = RetrievalService(config)
    
    s3_key = f"raw/{filename}"
    
    logger.info(f"🚀 Starting targeted ingestion for: {filename}")
    
    try:
        # Check if file exists in S3 first
        s3 = boto3.client(
             's3',
             aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
             aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
             region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        try:
             s3.head_object(Bucket=os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026"), Key=s3_key)
        except Exception:
             logger.error(f"❌ File not found in S3: {s3_key}")
             return

        # Ingest
        parent_chunks = await ingestion.process_file(s3_key, check_processed=False)
        
        if parent_chunks:
            logger.info(f"💾 Indexing {len(parent_chunks)} chunks...")
            retrieval.add_documents(parent_chunks)
            
            # Update SQL
            db = SessionLocal()
            # Check if record exists (maybe FAILED or missing)
            record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
            if record:
                record.status = "COMPLETED"
            else:
                record = FileTracking(filename=filename, status="COMPLETED")
                db.add(record)
            db.commit()
            db.close()
            
            logger.info(f"✅ Successfully ingested: {filename}")
        else:
            logger.warning(f"⚠️ Processed but no chunks generated for: {filename}")
            
    except Exception as e:
        logger.error(f"❌ Failed to ingest {filename}: {e}")

if __name__ == "__main__":
    # Robustly find the key first
    target_substring = "25016_FME"
    
    print(f"🔎 Scanning S3 for file matching: {target_substring}")
    load_dotenv()
    
    s3 = boto3.client(
         's3',
         aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
         aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
         region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    
    response = s3.list_objects_v2(Bucket=os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026"), Prefix='raw/')
    found_key = None
    
    for obj in response.get('Contents', []):
        if target_substring.lower() in obj['Key'].lower():
            found_key = obj['Key']
            break
            
    if found_key:
        print(f"✅ Found exact S3 Key: '{found_key}'")
        # Pass ONLY the filename part to ingest_file if it constructs key, 
        # OR better, update ingest_file to take full key.
        # ingest_file logic: s3_key = f"raw/{filename}"
        # We need to adjust ingest_file to accept full key or strip raw/
        
        # Let's adjust ingest_file call to just pass the filename part (stripping raw/)
        # found_key is like "raw/ISO..."
        filename_only = Path(found_key).name
        asyncio.run(ingest_file(filename_only))
    else:
        print("❌ Could not find file in S3 listing!")
