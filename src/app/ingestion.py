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
    
    def _check_rotation(self, pdf_path):
        """Check if PDF has rotated pages using PyMuPDF (FREE - Local)"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            has_rotation = any(page.rotation != 0 for page in doc)
            doc.close()
            return has_rotation
        except Exception as e:
            logger.warning(f"Could not check rotation: {e}")
            return False
    
    def _auto_rotate_pdf(self, pdf_path):
        """Auto-fix rotation and return corrected path (FREE - Local)"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            
            # Fix rotation for all pages
            for page in doc:
                if page.rotation != 0:
                    page.set_rotation(0)
            
            # Save to temp file with _fixed suffix
            fixed_path = str(pdf_path).replace('.pdf', '_fixed.pdf')
            doc.save(fixed_path)
            doc.close()
            
            logger.info(f"✅ Auto-rotated PDF: {fixed_path}")
            return Path(fixed_path)
        except Exception as e:
            logger.error(f"Failed to auto-rotate PDF: {e}")
            return pdf_path  # Return original if fix fails

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
                    # FIX #7: Close DB before early return
                    db.close()
                    return []
            finally:
                # Redundant but safe
                if db:
                    db.close()

        logger.info(f"Downloading {s3_key} from S3...")
        
        # FIX #5: Add S3 timeout configuration
        from botocore.config import Config
        from botocore.exceptions import ClientError, BotoCoreError
        
        s3_config = Config(
            connect_timeout=10,
            read_timeout=60,
            retries={'max_attempts': 3}
        )
        
        # Setup S3 Client with timeout
        s3_with_timeout = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            config=s3_config
        )
        
        # Create Temp File with Retry Logic
        # FIX #8: Use specific exception types (not generic Exception)
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((ClientError, BotoCoreError, ConnectionError)),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        def download_with_retry():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                s3_with_timeout.download_fileobj(bucket_name, s3_key, tmp)
                return Path(tmp.name)
        
        # FIX #2: Track original temp path separately
        original_temp_path = download_with_retry()
        temp_path = original_temp_path
            
        # Track metadata for enrichment
        fixed_pdf_path = None
        rotation_detected = False
        parsing_method = "unknown"
        
        try:
            # 1. ROTATION DETECTION AND AUTO-FIX (FREE - PyMuPDF)
            if self._check_rotation(temp_path):
                rotation_detected = True
                logger.warning(f"⚠️ Rotation detected in {filename}")
                fixed_pdf_path = self._auto_rotate_pdf(temp_path)
                # Use the corrected PDF for parsing
                temp_path = fixed_pdf_path
            
            logger.info(f"Processing {filename} with LlamaParse (Vendor Multimodal Only)...")
            
            # CLEAN VENDOR MULTIMODAL CONFIGURATION (No premium_mode conflict)
            parser = LlamaParse(
                result_type="markdown",
                verbose=True,
                language=self.config['parsing']['language'],
                use_vendor_multimodal_model=True,
                vendor_multimodal_model_name="gemini-2.5-flash",
                vendor_multimodal_api_key=os.getenv("GOOGLE_API_KEY"),
                # Using system_prompt instead of deprecated parsing_instruction
                system_prompt="""You are analyzing a technical PDF document that may contain rotated content.

CRITICAL EXTRACTION REQUIREMENTS:

📊 FOR GRAPHS/CHARTS (including rotated/sideways):
- Extract EVERY bar label with exact values and units
- Example: "Wohnraum: 74 dBA", "Dieselbox: 112 dBA"
- Include chart titles, figure numbers (e.g., "Bild 17.17")
- Preserve original language (German/Swedish/English)

📋 FOR TABLES:
- Extract as complete markdown tables
- Include ALL rows, columns, headers, units
- Do NOT round numeric values

🎯 STRICT RULES:
- Do NOT summarize - extract verbatim
- Handle rotated content (90°, 180°, 270°)
- Read small/faint text carefully
- Preserve ALL technical terminology exactly"""
            )
            
            # 2. Execute Parse with Retry
            try:
                 documents = await self._parse_with_retry(parser, str(temp_path))
                 if not documents:
                     raise ValueError("LlamaParse returned empty documents.")
                 parsing_method = "multimodal"
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
                    parsing_method = "text_fallback"
                    logger.info(f"Fallback parsing successful for {filename}")
                except Exception as e2:
                    logger.error(f"Processing failed for {filename} after retries and fallback: {e2}")
                    raise e2
            
            
            # Assemble full text with page markers
            full_text_parts = []
            for i, doc in enumerate(documents):
                # FIX #10: Validate page number (fallback to index if invalid)
                page_num = doc.metadata.get('page_label', '')
                if not page_num or str(page_num).strip() == '':
                    page_num = str(i + 1)  # Use 1-indexed page number as fallback
                
                page_marker = f"\n\n--- [PAGE {page_num}] ---\n"
                full_text_parts.append(page_marker + doc.text)
                
            full_text = "".join(full_text_parts)
            
            # Check for encoding issues (garbled text) - Warning only
            garbled_count = full_text.count('�')
            if garbled_count > 10:
                logger.warning(f"⚠️ Possible encoding issues in {filename}: {garbled_count} replacement characters found")
            
            logger.info(f"✅ Extraction Complete: {len(full_text)} characters extracted, {len(documents)} pages")
            
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
            
            # FIX #6: Validate that chunking produced results
            if not parent_chunks or len(parent_chunks) == 0:
                error_msg = f"Chunking failed for {filename}: No parent chunks created from {len(full_text)} chars"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✅ Created {len(parent_chunks)} parent chunks")
            
            # 4. METADATA ENRICHMENT
            from datetime import datetime
            ingestion_timestamp = datetime.utcnow().isoformat()
            
            for chunk in parent_chunks:
                chunk.metadata.update({
                    'source': filename,
                    'ingestion_timestamp': ingestion_timestamp,
                    'parsing_method': parsing_method,
                    'rotation_fixed': rotation_detected,
                    'model_version': 'gemini-2.5-flash',
                    'total_chunks': len(parent_chunks)
                })
            
            logger.info(f"📊 Ingestion Summary for {filename}:")
            logger.info(f"   - Rotation Fixed: {rotation_detected}")
            logger.info(f"   - Parsing Method: {parsing_method}")
            logger.info(f"   - Total Pages: {len(documents)}")
            logger.info(f"   - Total Chunks: {len(parent_chunks)}")
            logger.info(f"   - Avg Chunk Size: {len(full_text) // len(parent_chunks) if parent_chunks else 0} chars")
            
            return parent_chunks
        
        finally:
            # FIX #2: Cleanup both original and fixed PDFs properly
            # Cleanup original downloaded PDF
            if original_temp_path and original_temp_path.exists():
                try:
                    original_temp_path.unlink()
                    logger.debug(f"🧹 Cleaned up original temp file: {original_temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete original temp file: {e}")
            
            # Cleanup fixed PDF if it was created (and is different from original)
            if fixed_pdf_path and fixed_pdf_path.exists() and fixed_pdf_path != original_temp_path:
                try:
                    fixed_pdf_path.unlink()
                    logger.debug(f"🧹 Cleaned up fixed PDF: {fixed_pdf_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete fixed PDF: {e}")

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
                    
                    # FIX #4: Sanitize broker URL before logging (prevent credential leak)
                    from src.worker.celery_app import app
                    broker_url = app.conf.broker_url
                    # Hide password if present (redis://:password@host:port/db)
                    broker_url_safe = broker_url.split('@')[-1] if '@' in broker_url else broker_url
                    logger.info(f"DEBUG: Using Celery Broker: {broker_url_safe}")
                    
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
