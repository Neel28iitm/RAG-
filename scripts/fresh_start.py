"""
Script: scripts/fresh_start.py
Purpose: Complete System Reset & Safe Re-ingestion
Usage: python scripts/fresh_start.py
"""

import os
import sys
import boto3
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add Project Root to Path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.config import load_config
from src.core.database import SessionLocal
from src.core.models import FileTracking
from src.app.retrieval import RetrievalService
from src.app.ingestion import DocumentIngestion
from src.core.vector_store import get_qdrant_client

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fresh_start')

def clear_system(config):
    """Wipes all data from Qdrant, S3 Parent Store, and SQL Tracking"""
    logger.info("🔥 STARTING SYSTEM PURGE...")
    
    # 1. Clear Qdrant & S3 Parent Store
    try:
        retrieval = RetrievalService(config)
        retrieval.clear() # This clears Qdrant collection and S3 parent_store/
        logger.info("✅ Qdrant & S3 Parent Store Cleared.")
    except Exception as e:
        logger.error(f"❌ Failed to clear Retrieval System: {e}")
        # Don't stop, try to clear SQL at least

    # 2. Clear SQL Tracking
    try:
        db = SessionLocal()
        num_deleted = db.query(FileTracking).delete()
        db.commit()
        db.close()
        logger.info(f"✅ SQL Tracking Cleared. ({num_deleted} records removed)")
    except Exception as e:
        logger.warning(f"⚠️ SQL Clear failed (might be empty): {e}")

async def ingest_all_files(config):
    """Synchronously processes all files from S3 raw/"""
    logger.info("📥 STARTING FRESH INGESTION...")
    
    ingestion = DocumentIngestion(config)
    retrieval = RetrievalService(config) # Init Retrieval for indexing
    
    # 1. List Files from S3 Raw
    bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
    prefix = "raw/"
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].lower().endswith('.pdf')]
        
        if not files:
            logger.error("❌ No PDF files found in S3 raw/ folder!")
            return

        logger.info(f"📋 Found {len(files)} documents to ingest.")
        
        success_count = 0
        failed_files = []

        for i, s3_key in enumerate(files):
            filename = Path(s3_key).name
            logger.info(f"🔄 Processing [{i+1}/{len(files)}]: '{filename}'")
            
            try:
                # Direct Process Call (No Celery)
                # Note: We pass the raw S3 key. verify spaces are handled.
                parent_chunks = await ingestion.process_file(s3_key, check_processed=False)
                
                if parent_chunks:
                    retrieval.add_documents(parent_chunks)
                    
                else:
                    logger.warning(f"⚠️ No chunks generated for {filename}")
                    
                
                # Mark as Completed in SQL (Manually since we skipped Celery task)
                db = SessionLocal()
                record = FileTracking(filename=filename, status="COMPLETED")
                db.add(record)
                db.commit()
                db.close()
                
                logger.info(f"✅ Success: '{filename}'")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ FAILED: '{filename}' - Reason: {e}")
                failed_files.append(filename)

        print("\n" + "="*40)
        print(f"🎉 INGESTION COMPLETE")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed:     {len(failed_files)}")
        if failed_files:
            print("Failed Files:")
            for f in failed_files:
                print(f" - {f}")
        print("="*40 + "\n")

    except Exception as e:
        logger.error(f"Fatal Error during ingestion loop: {e}")

if __name__ == "__main__":
    load_dotenv()
    
    try:
        config = load_config()
        
        # Confirmation
        print("⚠️  WARNING: This will DELETE ALL DATA and re-ingest everything.")
        # Auto-proceed as per user request for "Fresh Start"
        
        clear_system(config)
        asyncio.run(ingest_all_files(config))
        
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    except Exception as e:
        logger.critical(f"Script crashed: {e}")
