from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
import logging
import time
import json
import os
import sys

# Force UTF-8 for Windows Console
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# --- INTEGRATION IMPORTS (Active) ---
from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.app.memory import MemoryService
import phoenix as px
from openinference.instrumentation.langchain import LangChainInstrumentor

# --- OBSERVABILITY SETUP (Active) ---
# Launches Phoenix Tracing Server (localhost:6006)
session = px.launch_app()
# Auto-instruments all LangChain components in this process
LangChainInstrumentor().instrument()

app = FastAPI(
    title="RAG AI Backend Service",
    version="1.0",
    description="Public RAG API with Hybrid Search and Streaming Support",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

# --- INITIALIZATION (Active) ---
try:
    config = load_config()
    retrieval_service = RetrievalService(config)
    generation_service = GenerationService(config)
    memory_service = MemoryService() # Uses env REDIS_URL
    logger.info("✅ Core RAG Services Initialized Successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize RAG Services: {e}")
    raise e

# --- MODELS ---

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's question")
    session_id: str = Field(default="default_session", description="Session ID for chat history")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    top_k: int = Field(default=5, description="Number of documents to retrieve")
    stream: bool = Field(default=False, description="Enable streaming response")

class SourceDoc(BaseModel):
    title: str
    page: int
    snippet: str

class ResponseMetadata(BaseModel):
    response_time: str
    tokens_used: int # Placeholder

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceDoc]
    metadata: ResponseMetadata

# --- ENDPOINTS ---

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    start_time = time.time()
    logger.info(f"Received query: {request.query} (Session: {request.session_id}, Stream: {request.stream})")
    
    try:
        # 1. Fetch History
        chat_history = memory_service.get_history(request.session_id)
        
        # 2. Get Context (History-Aware)
        # 2. Get Context (History-Aware)
        context_docs, metrics = retrieval_service.get_relevant_docs(
            request.query, 
            top_k=request.top_k, 
            chat_history=chat_history
        )
        
        # Helper to format sources
        real_sources = []
        for doc in context_docs:
            src_name = doc.metadata.get('source', 'unknown')
            pg_num = doc.metadata.get('page_label', 0)
            try:
                pg_num = int(pg_num)
            except:
                pg_num = 0
            real_sources.append(SourceDoc(
                title=src_name,
                page=pg_num,
                snippet=doc.page_content[:200].replace("\n", " ") + "..."
            ))

        # --- BRANCH: STREAMING ---
        if request.stream:
            async def event_generator():
                # 1. Send Sources Event First (Custom Event)
                sources_json = json.dumps([s.dict() for s in real_sources])
                yield f"event: sources\ndata: {sources_json}\n\n"
                
                # 2. Stream Answer
                full_answer = ""
                try:
                    # Note: Using synchronous iterator from generation_service is fine in async def with FastAPI
                    # if it's not blocking completely (LLM calls are network IO).
                    # Ideally generation_service should be async, but for now we iterate.
                    iterator = generation_service.stream_answer(
                        original_query=request.query, 
                        retrieved_docs=context_docs,
                        chat_history=chat_history
                    )
                    
                    for chunk in iterator:
                        full_answer += chunk
                        # Send text chunk
                        yield f"data: {chunk}\n\n"
                        
                    # 3. Save to Memory
                    memory_service.add_user_message(request.session_id, request.query)
                    memory_service.add_ai_message(request.session_id, full_answer)
                    
                    yield "event: done\ndata: [DONE]\n\n"
                    
                except Exception as e:
                    yield f"event: error\ndata: {str(e)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # --- BRANCH: STANDARD JSON ---
        else:
            ai_answer = generation_service.generate_answer(
                original_query=request.query, 
                retrieved_docs=context_docs,
                chat_history=chat_history
            )
            
            # Save to Memory
            memory_service.add_user_message(request.session_id, request.query)
            memory_service.add_ai_message(request.session_id, ai_answer)
            
            duration = time.time() - start_time
            
            return ChatResponse(
                answer=ai_answer,
                sources=real_sources,
                metadata=ResponseMetadata(
                    response_time=f"{duration:.2f}s",
                    tokens_used=0 # Placeholder
                )
            )

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
