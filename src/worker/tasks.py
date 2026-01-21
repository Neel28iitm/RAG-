import asyncio
from pathlib import Path
from datetime import datetime
from celery.utils.log import get_task_logger

from src.worker.celery_app import app
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from src.core.database import get_db
from src.core.models import FileTracking

logger = get_task_logger(__name__)

@app.task(bind=True, max_retries=3)
def process_document_task(self, file_path_str: str, config: dict):
    db = next(get_db())
    filename = Path(file_path_str).name
    
    try:
        # FIX #13: Add timing metrics
        import time
        task_start = time.time()
        
        logger.info(f"Task Started: {filename}")
        
        # Update Status to PROCESSING
        tracking = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        if not tracking:
            # Should exist from producer, but just in case
            tracking = FileTracking(filename=filename, status="PROCESSING")
            db.add(tracking)
        else:
            tracking.status = "PROCESSING"
            tracking.error_msg = None # Clear previous errors
            
        tracking.updated_at = datetime.utcnow()
        db.commit()
        
        # 1. Parsing (Async wrapper)
        ingestor = DocumentIngestion(config)
        
        # Clean Async Run
        try:
             # Create a new loop for this task execution to ensure isolation
             loop = asyncio.new_event_loop()
             asyncio.set_event_loop(loop)
             chunks = loop.run_until_complete(ingestor.process_file(Path(file_path_str), check_processed=False))
             loop.close()
        except Exception as e:
             logger.error(f"Async Loop Error: {e}")
             raise e
             
        # 2. Embedding / Indexing
        if chunks:
            retriever = RetrievalService(config)
            
            # FIX #1: Make vector operations and DB update ATOMIC
            # Only mark COMPLETED after successful vector storage
            try:
                # Delete existing vectors for this file before adding new ones
                retriever.delete_documents_by_source(filename)
                
                # Add new vectors
                retriever.add_documents(chunks)
                
                # ONLY NOW mark as COMPLETED (after successful vector storage)
                tracking.status = "COMPLETED"
                tracking.updated_at = datetime.utcnow()
                db.commit()
                
                # FIX #13: Log timing metrics
                task_duration = time.time() - task_start
                logger.info(f"✅ Task Success: {filename}")
                logger.info(f"📊 Total Processing Time: {task_duration:.2f}s")
                return f"SUCCESS: {filename}"
            except Exception as e_vector:
                # Vector storage failed - rollback and mark as FAILED
                logger.error(f"Vector storage failed for {filename}: {e_vector}")
                db.rollback()
                tracking.status = "FAILED"
                tracking.error_msg = f"Vector storage error: {str(e_vector)}"
                tracking.updated_at = datetime.utcnow()
                db.commit()
                raise e_vector
        else:
            # 3. Handle Empty Content (Silent Failure)
            error_msg = f"No chunks produced for {filename}. Triggering Retry."
            logger.warning(error_msg)
            # Raise exception to enforce Celery Retry (max_retries=3)
            raise ValueError(error_msg)
        
    except Exception as exc:
        logger.error(f"Task Failed: {filename} - {exc}")
        db.rollback()
        
        try:
            tracking = db.query(FileTracking).filter(FileTracking.filename == filename).first()
            if tracking:
                tracking.status = "FAILED"
                tracking.error_msg = str(exc)
                tracking.updated_at = datetime.utcnow()
                db.commit()
        except:
            pass # DB error during error handling
            
        # Retry logic
        raise self.retry(exc=exc, countdown=60)
        
    finally:
        db.close()
