
# 🚀 API Handover Guide for Developer

## Overview
This API connects to the **RAG System** backed by **Qdrant Cloud** (Vector Store) and **AWS S3** (Document Store).
It provides answers based on the uploaded PDF documents using Hybrid Search (Dense + Sparse).

## 📡 Endpoint Details
- **Base URL**: `http://localhost:8000`
- **Endpoint**: `POST /api/v1/chat`
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
## 📝 Request Format

**Body:**
```json
{
  "query": "Company ki leave policy kya hai?",
  "session_id": "user_123_chat_01",
  "top_k": 5,
  "stream": false
}
```

## ✅ Informative Response (Standard)
```json
{
  "answer": "Aap saal mein 15 paid leaves le sakte hain.",
  "sources": [
    {
      "title": "HR_Policy_2024.pdf",
      "page": 12,
      "snippet": "...employees are entitled to 15 days of annual leave..."
    }
  ],
  "metadata": {
    "response_time": "0.80s",
    "tokens_used": 0
  }
}
```

## 🌊 Streaming Mode
Set `"stream": true` in request.
Returns `text/event-stream` with these events:
1. `event: sources` -> JSON data of sources.
2. `data: ...` -> Text chunks.
3. `event: done` -> Stream finished.

---

## ⚙️ Logic Behind the API
1.  **Input**: Receives `query`.
2.  **Hybrid Search**: 
    - Converts query to Vector (Text Embedding 004).
    - Searches **Qdrant Cloud** (`rag_production` collection).
3.  **Parent Retrieval**: Fetches full context from **S3**.
4.  **Generation**: **Gemini 2.5 Flash** synthesizes the answer.

## 🛠️ Running Locally (Docker)
Ensure Docker is running:
```bash
docker-compose up -d api
```
The API will be available at port **8000**.
