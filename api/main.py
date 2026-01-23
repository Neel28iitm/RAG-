"""
FastAPI REST API for RAG System
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv('.env')

from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.config import load_config

# Initialize FastAPI app
app = FastAPI(
    title="RAG System API",
    description="Retrieval Augmented Generation API for document Q&A with multilingual support",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

# CORS - Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config and initialize services
config = load_config()
retrieval_service = RetrievalService(config)
generation_service = GenerationService(config)

# Request/Response Models
class QueryRequest(BaseModel):
    query: str = Field(..., description="User question in any language (English, Swedish, German)", min_length=3)
    chat_history: Optional[List[dict]] = Field(default=None, description="Previous conversation messages")
    top_k: Optional[int] = Field(default=10, description="Number of documents to retrieve (1-20)", ge=1, le=20)
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What are the noise requirements for office buildings according to SS 25268?",
                "chat_history": None,
                "top_k": 10
            }
        }

class Source(BaseModel):
    document: str = Field(..., description="Source document filename")
    page: Optional[str] = Field(None, description="Page number or label")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="Generated answer from RAG system")
    sources: List[Source] = Field(..., description="Source documents used")
    metrics: dict = Field(..., description="Performance metrics (retrieval time, reranking time, etc.)")
    
    class Config:
        schema_extra = {
            "example": {
                "answer": "According to SS 25268:2023, office spaces require a maximum reverberation time of 0.6 seconds for rooms under 250 m³.",
                "sources": [
                    {"document": "SS_25268_2023 Byggnadsakustik.pdf", "page": "Table 17"}
                ],
                "metrics": {
                    "retrieval_time": 3.2,
                    "reranking_time": 0.8,
                    "total_time": 4.5
                }
            }
        }

class HealthResponse(BaseModel):
    status: str
    services: dict

# API Endpoints

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API status check
    """
    return {
        "message": "RAG System API is running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint - verify all services are operational
    """
    try:
        # Check Qdrant connection
        qdrant_status = "healthy" if retrieval_service.client else "unavailable"
        
        # Check LLM
        llm_status = "healthy" if generation_service.llm_chain else "unavailable"
        
        return {
            "status": "healthy",
            "services": {
                "qdrant": qdrant_status,
                "llm": llm_status,
                "cohere_reranker": "healthy" if retrieval_service.cohere_client else "unavailable"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(
    request: QueryRequest,
    x_api_key: Optional[str] = Header(None, description="Optional API key for authentication")
):
    """
    Main RAG query endpoint
    
    **Process:**
    1. Retrieves relevant documents from vector store (Qdrant)
    2. Reranks results using Cohere multilingual reranker
    3. Generates answer using Google Gemini 2.5 Flash
    
    **Supported Languages:**
    - English
    - Swedish (Svenska)
    - German (Deutsch)
    
    **Example Queries:**
    - "What is the maximum noise level for preschools?"
    - "Vad är efterklangstiden för kontor enligt SS 25268?"
    - "Welche Lärmschutzanforderungen gelten für Büros?"
    """
    try:
        # Optional: API key validation
        # if x_api_key != os.getenv("API_KEY"):
        #     raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Step 1: Retrieve documents
        docs, metrics = retrieval_service.get_relevant_docs(
            query=request.query,
            top_k=request.top_k,
            chat_history=request.chat_history
        )
        
        if not docs:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found for your query"
            )
        
        # Step 2: Generate answer
        answer = generation_service.generate_answer(
            query=request.query,
            retrieved_docs=docs,
            chat_history=request.chat_history
        )
        
        # Step 3: Extract sources
        sources = []
        seen_sources = set()
        for doc in docs:
            source_name = doc.metadata.get('source', 'Unknown')
            if source_name not in seen_sources:
                sources.append(Source(
                    document=source_name,
                    page=doc.metadata.get('page_label')
                ))
                seen_sources.add(source_name)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            metrics={
                "retrieval_time": round(metrics.get('time_retrieval', 0), 2),
                "reranking_time": round(metrics.get('time_rerank', 0), 2),
                "total_time": round(
                    metrics.get('time_retrieval', 0) + metrics.get('time_rerank', 0),
                    2
                )
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/documents", tags=["Documents"])
async def list_documents():
    """
    List all indexed documents in the system
    """
    try:
        # Get unique documents from Qdrant
        scroll_result = retrieval_service.client.scroll(
            collection_name=retrieval_service.collection_name,
            limit=100,
            with_payload=True
        )
        
        sources = set()
        for point in scroll_result[0]:
            source = point.payload.get('metadata', {}).get('source')
            if source:
                sources.add(source)
        
        return {
            "count": len(sources),
            "documents": sorted(list(sources))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

# Run with: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
