"""
Module: Ingestion
Purpose: Handle loading of documents (PDFs) using LlamaParse with Vendor Multimodal (Cost Optimized).
Refactored to use Celery + Redis for Task Queueing.
"""

import os
import logging
import asyncio
import tempfile
import boto3
from pathlib import Path
from llama_parse import LlamaParse
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from src.core.database import get_db
from src.core.models import FileTracking
from datetime import datetime

logger = logging.getLogger('app_logger')

class DocumentIngestion:
    def __init__(self, config):
        self.config = config
        self.data_raw = Path(config['paths']['data_raw'])
        self.should_clear_db = False 
        # Note: Config change detection removed for now in Queue architecture shift.
        # To restore, implement a ConfigTracking table.

    async def process_file(self, file_path, check_processed=True):
        """Processes a single PDF file using Optimized LlamaParse Settings"""
        check_db = check_processed
        
        # S3 Download Logic
        bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
        s3_key = str(file_path).replace("\\", "/") # Ensure forward slashes for S3
        filename = Path(s3_key).name
        
        # Setup S3 Client
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

        if check_db:
            db = next(get_db())
            try:
                exists = db.query(FileTracking).filter(
                    FileTracking.filename == filename,
                    FileTracking.status == "COMPLETED"
                ).first()
                if exists:
                    logger.info(f"Skipping {filename} (Already processed)")
                    return []
            finally:
                db.close()

        logger.info(f"Downloading {s3_key} from S3...")
        
        # Create Temp File
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            s3.download_fileobj(bucket_name, s3_key, tmp)
            temp_path = Path(tmp.name)
            
        try:
            logger.info(f"Processing {filename} with LlamaParse (Vendor Multimodal Mode)...")
            
            # 1. OPTIMIZED PARSING CONFIGURATION
            parser = LlamaParse(
                result_type="markdown",
                verbose=True,
                language=self.config['parsing']['language'],
                use_vendor_multimodal_model=True,
                vendor_multimodal_model_name="gemini-2.0-flash-exp",
                vendor_multimodal_api_key=os.getenv("GOOGLE_API_KEY"),
                parsing_instruction="Extract all tables as Markdown formatted text. Do not summarize tables. Extract all charts and graphs as detailed text descriptions.",
            )
            
            # 2. Execute Parse with Retry
            try:
                 documents = await self._parse_with_retry(parser, str(temp_path))
                 if not documents:
                     raise ValueError("LlamaParse returned empty documents.")
            except Exception as e:
                logger.warning(f"Multimodal Parsing failed for {filename}: {e}. Retrying with Standard Text Mode...")
                # Log the specific error for debugging
                logger.error(f"DEBUG: Multimodal failure reason: {str(e)}")
                try:
                    # FALLBACK: Standard Mode (No Vendor Multimodal)
                    fallback_parser = LlamaParse(
                        result_type="text",
                        verbose=True,
                        language=self.config['parsing']['language']
                    )
                    documents = await self._parse_with_retry(fallback_parser, str(temp_path))
                    logger.info(f"Fallback parsing successful for {filename}")
                except Exception as e2:
                    logger.error(f"Processing failed for {filename} after retries and fallback: {e2}")
                    raise e2
            
            full_text_parts = []
            for doc in documents:
                page_num = doc.metadata.get('page_label', 'Unknown')
                page_marker = f"\n\n--- [PAGE {page_num}] ---\n"
                full_text_parts.append(page_marker + doc.text)
                
            full_text = "".join(full_text_parts)
            
            # 3. Double-Pass Chunking
            logger.info("Chunking content (Parent Chunks)...")
            
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            md_header_splits = markdown_splitter.split_text(full_text)
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.config['parsing']['chunk_size'],
                chunk_overlap=self.config['parsing']['chunk_overlap']
            )
            
            parent_chunks = text_splitter.split_documents(md_header_splits)
            
            for chunk in parent_chunks:
                chunk.metadata['source'] = filename
            
            return parent_chunks
        
        finally:
            # Cleanup Temp File
            if temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"🧹 Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception), 
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def _parse_with_retry(self, parser, file_path_str):
        """Helper to retry parsing on failure"""
        return await parser.aload_data(file_path_str)

    async def ingest_documents(self):
        """Producer: Scan files and Queue tasks"""
        # Local import to avoid circular dependency
        from src.worker.tasks import process_document_task
        
        bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
        prefix = "raw/"
        
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            
            # Filter only PDFs
            files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].lower().endswith('.pdf')]
            
        except Exception as e:
            logger.error(f"❌ Failed to list S3 objects: {e}")
            return []

        if not files:
            logger.info("No PDF files found in S3 raw/ folder")
            return []
            
        logger.info(f"Found {len(files)} files. Checking queue status...")
        
        queued_count = 0
        db = next(get_db())
        try:
            for s3_key in files:
                filename = Path(s3_key).name
                
                # Check DB Status
                record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
                
                # Logic: Queue if NOT exists OR if FAILED (retry)
                # Skip if PENDING/PROCESSING/COMPLETED
                should_queue = False
                if not record:
                    should_queue = True
                    record = FileTracking(filename=filename, status="PENDING")
                    db.add(record)
                elif record.status == "FAILED":
                    should_queue = True
                    record.status = "PENDING"
                    record.error_msg = None
                    # Update timestamp
                    record.updated_at = datetime.utcnow()
                
                if should_queue:
                    db.commit() # Commit PENDING status
                    
                    # DEBUG: Print Broker URL
                    from src.worker.celery_app import app
                    logger.info(f"DEBUG: Using Celery Broker: {app.conf.broker_url}")
                    
                    # Send to Celery
                    process_document_task.delay(s3_key, self.config)
                    logger.info(f"🚀 Queued: {filename}")
                    queued_count += 1
                else:
                    logger.info(f"ℹ️  Skipping {filename} (Status: {record.status})")
                    
        except Exception as e:
            logger.error(f"Error during queuing: {e}")
        finally:
            db.close()
            
        if queued_count > 0:
            logger.info(f"✅ Successfully queued {queued_count} document(s). Workers will process them in background.")
        
        # Return empty list because we are async now, we don't return chunks synchronously
        return []
