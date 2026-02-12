import asyncio
from pathlib import Path
from datetime import datetime
from celery import Task
from celery.utils.log import get_task_logger

from src.worker.celery_app import app
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.database import get_db
from src.core.models import FileTracking

logger = get_task_logger(__name__)


@app.task(bind=True)
def process_query_task(self, query: str, config: dict, top_k: int = 10, chat_history: list = None):
    """
    Process RAG query asynchronously with progress tracking
    
    Args:
        self: Task instance (bind=True for progress updates)
        query: User question
        config: RAG configuration dict
        top_k: Number of documents to retrieve
        chat_history: Previous chat messages (optional)
    
    Returns:
        dict: {
            "answer": str,
            "sources": list,
            "metrics": dict
        }
    
    Progress Stages:
        0%: Task started
        30%: Document retrieval complete
        70%: Reranking complete
        100%: Answer generation complete
    """
    try:
        import time
        
        # Stage 0: Initialize (0%)
        self.update_state(
            state='PROCESSING',
            meta={'progress': 0, 'message': 'Starting query processing...'}
        )
        logger.info(f"🔍 Query task started: {query[:50]}...")
        
        # Stage 1: Retrieval (0% → 30%)
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'message': 'Searching documents...'}
        )
        
        start_retrieval = time.time()
        retrieval_service = RetrievalService(config)
        
        # Convert chat_history to proper format if needed
        from langchain_core.messages import HumanMessage, AIMessage
        lc_history = []
        if chat_history:
            for msg in chat_history:
                if msg.get("role") == "user":
                    lc_history.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    lc_history.append(AIMessage(content=msg["content"]))
        
        docs, metrics = retrieval_service.get_relevant_docs(
            query=query,
            top_k=top_k,
            chat_history=lc_history if lc_history else None
        )
        retrieval_time = time.time() - start_retrieval
        
        if not docs:
            self.update_state(
                state='FAILURE',
                meta={'progress': 100, 'error': 'No relevant documents found'}
            )
            return {
                "error": "NO_DOCUMENTS_FOUND",
                "message": "No relevant information found for your query"
            }
        
        # Stage 2: Reranking complete (30% → 70%)
        self.update_state(
            state='PROCESSING',
            meta={'progress': 30, 'message': 'Documents retrieved. Analyzing...'}
        )
        
        # Simulate reranking progress (already done in retrieval_service)
        time.sleep(0.5)  # Small delay for smoother UX
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 70, 'message': 'Generating answer...'}
        )
        
        # Stage 3: Generation (70% → 100%)
        start_generation = time.time()
        generation_service = GenerationService(config)
        
        answer = generation_service.generate_answer(
            query=query,
            retrieved_docs=docs,
            chat_history=lc_history if lc_history else None
        )
        generation_time = time.time() - start_generation
        
        # Extract sources
        sources = []
        seen_sources = set()
        for doc in docs:
            source_name = doc.metadata.get('source', 'Unknown')
            if source_name not in seen_sources:
                sources.append({
                    'document': source_name,
                    'page': doc.metadata.get('page_label')
                })
                seen_sources.add(source_name)
        
        # Stage 4: Complete (100%)
        result = {
            "answer": answer,
            "sources": sources,
            "metrics": {
                "retrieval_time": round(retrieval_time, 2),
                "reranking_time": round(metrics.get('rerank_seconds', 0), 2),
                "generation_time": round(generation_time, 2),
                "total_time": round(retrieval_time + generation_time, 2)
            }
        }
        
        self.update_state(
            state='SUCCESS',
            meta={'progress': 100, 'message': 'Complete!', 'result': result}
        )
        
        logger.info(f"✅ Query completed in {result['metrics']['total_time']:.2f}s")
        return result
        
    except Exception as exc:
        logger.error(f"❌ Query task failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'progress': 100, 'error': str(exc)}
        )
        raise


# Custom Retry Task with exponential backoff
class RetryableIngestionTask(Task):
    """
    Custom task class with automatic retry configuration
    """
    autoretry_for = (
        ConnectionError,
        TimeoutError,
        Exception  # Retry on any exception
    )
    retry_kwargs = {
        'max_retries': 3,
        'countdown': 5  # Initial wait: 5 seconds
    }
    retry_backoff = True  # Exponential: 5s, 25s, 125s
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add randomness to prevent thundering herd


@app.task(base=RetryableIngestionTask, bind=True)
def process_document_task(self, file_path_str: str, config: dict):
    """
    Process document with automatic retry on failures
    
    Args:
        self: Task instance (bind=True gives access)
        file_path_str: Path to PDF file
        config: Configuration dict
    """
    db = next(get_db())
    filename = Path(file_path_str).name
    retry_count = self.request.retries  # 0, 1, 2, or 3
    
    try:
        # Timing metrics
        import time
        task_start = time.time()
        
        logger.info(f"{'🔄 RETRY' if retry_count > 0 else '🚀 START'} Task: {filename} (Attempt {retry_count + 1}/4)")
        
        # Get or create tracking record
        tracking = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        if not tracking:
            tracking = FileTracking(filename=filename, status="PROCESSING")
            db.add(tracking)
        else:
            # Update status with retry info
            if retry_count > 0:
                tracking.status = f"RETRY_{retry_count}"
                logger.warning(f"⚠️ Retry attempt {retry_count}/3 for {filename}")
            else:
                tracking.status = "PROCESSING"
            
            tracking.error_msg = None  # Clear previous errors
            
        tracking.updated_at = datetime.utcnow()
        db.commit()
        
        # 1. Parsing
        ingestor = DocumentIngestion(config)
        
        try:
            # Create isolated event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chunks = loop.run_until_complete(
                ingestor.process_file(Path(file_path_str), check_processed=False)
            )
            loop.close()
        except Exception as e:
            logger.error(f"Parsing error: {e}")
            raise e  # Re-raise to trigger retry
              
        # 2. Embedding & Indexing
        if chunks:
            retriever = RetrievalService(config)
            
            # ATOMIC: Vector operations and DB update
            try:
                # Delete existing vectors first
                retriever.delete_documents_by_source(filename)
                
                # Add new vectors
                retriever.add_documents(chunks)
                
                # Mark COMPLETED only after successful vector storage
                tracking.status = "COMPLETED"
                tracking.updated_at = datetime.utcnow()
                db.commit()
                
                # Log success with timing
                task_duration = time.time() - task_start
                logger.info(f"✅ SUCCESS: {filename} processed in {task_duration:.2f}s (after {retry_count} retries)")
                return f"SUCCESS: {filename}"
                
            except Exception as e_vector:
                # Vector storage failed - rollback
                logger.error(f"Vector storage failed: {e_vector}")
                db.rollback()
                
                # Update tracking
                tracking.status = "FAILED" if self.request.retries >= 3 else f"RETRY_{retry_count + 1}"
                tracking.error_msg = f"Vector storage error: {str(e_vector)}"
                tracking.updated_at = datetime.utcnow()
                db.commit()
                
                raise e_vector  # Re-raise to trigger retry
        else:
            # No chunks produced
            error_msg = f"No chunks produced for {filename}"
            logger.warning(error_msg)
            raise ValueError(error_msg)  # Trigger retry
        
    except Exception as exc:
        logger.error(f"❌ Task error for {filename}: {exc}")
        db.rollback()
        
        # Update tracking
        try:
            tracking = db.query(FileTracking).filter(FileTracking.filename == filename).first()
            if tracking:
                # Check if max retries exhausted
                if self.request.retries >= 3:
                    # Final failure
                    tracking.status = "FAILED"
                    tracking.error_msg = str(exc)[:500]  # Truncate long errors
                    logger.error(f"🔴 FINAL FAILURE for {filename} after 3 retries")
                else:
                    # Will retry
                    tracking.status = f"RETRY_{retry_count + 1}"
                    next_wait = 5 * (2 ** retry_count)  # Exponential backoff
                    logger.warning(f"⏳ Will retry {filename} in ~{next_wait}s")
                
                tracking.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e_tracking:
            logger.error(f"Failed to update tracking: {e_tracking}")
            pass
        
        db.close()
        raise  # Re-raise to trigger Celery auto-retry mechanism
        
    finally:
        db.close()

