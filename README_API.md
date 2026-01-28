
# 🚀 API Handover Guide for Developer

## Overview
This API connects to the **RAG System** backed by **Qdrant Cloud** (Vector Store) and **AWS S3** (Document Store).
It provides answers based on the uploaded PDF documents using Hybrid Search (Dense + Sparse).

---

## 📡 API Endpoints

### 1️⃣ **Document Status API** (NEW! 🎉)

#### Check Single Document Status
- **Endpoint**: `GET /document/status/{docname}`
- **Use Case**: Track if a specific file has been ingested or not

**Example Request:**
```bash
curl -X GET "http://localhost:8000/document/status/company_policy.pdf"
```

**Response:**
```json
{
  "filename": "company_policy.pdf",
  "status": "COMPLETED",
  "created_at": "2026-01-28T10:00:00",
  "updated_at": "2026-01-28T10:05:00",
  "error_msg": null
}
```

**Status Values:**
- `PENDING` - Document queued for ingestion
- `PROCESSING` - Document currently being ingested
- `COMPLETED` - Ingestion successful, ready for queries ✅
- `FAILED` - Ingestion failed (check `error_msg`)

---

#### Get All Documents Status
- **Endpoint**: `GET /documents/status`
- **Use Case**: Get ingestion status of ALL documents (dashboard view)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/documents/status"
```

**Response:**
```json
{
  "count": 2,
  "documents": [
    {
      "filename": "company_policy.pdf",
      "status": "COMPLETED",
      "created_at": "2026-01-28T10:00:00",
      "updated_at": "2026-01-28T10:05:00",
      "error_msg": null
    },
    {
      "filename": "HR_Handbook.pdf",
      "status": "PROCESSING",
      "created_at": "2026-01-28T10:10:00",
      "updated_at": "2026-01-28T10:10:30",
      "error_msg": null
    }
  ]
}
```

---

### 2️⃣ **Query API** (Question Answering)

- **Endpoint**: `POST /query`
- **Use Case**: Ask questions from ingested documents

**Request Format:**
```json
{
  "query": "Company ki leave policy kya hai?",
  "chat_history": null,
  "top_k": 10
}
```

**Response (Standard):**
```json
{
  "answer": "Aap saal mein 15 paid leaves le sakte hain.",
  "sources": [
    {
      "document": "HR_Policy_2024.pdf",
      "page": "12"
    }
  ],
  "metrics": {
    "retrieval_time": 3.2,
    "reranking_time": 0.8,
    "total_time": 4.5
  }
}
```

---

## 💡 Developer Workflow Example

```bash
# Step 1: Upload document (via your upload API - not shown here)
# ... upload company_policy.pdf ...

# Step 2: Check if ingestion is complete
curl -X GET "http://localhost:8000/document/status/company_policy.pdf"
# Response: {"status": "PROCESSING"}

# Step 3: Wait and check again
sleep 60
curl -X GET "http://localhost:8000/document/status/company_policy.pdf"
# Response: {"status": "COMPLETED"}

# Step 4: Now query the document!
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the leave policy?", "top_k": 10}'
```

---

## ⚙️ Logic Behind the API
1.  **Input**: Receives `query`.
2.  **Hybrid Search**: 
    - Converts query to Vector (Text Embedding 004).
    - Searches **Qdrant Cloud** (`rag_production` collection).
3.  **Parent Retrieval**: Fetches full context from **S3**.
4.  **Generation**: **Gemini 2.5 Flash** synthesizes the answer.

---

## 🛠️ Running Locally

### Start API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Or with Docker
```bash
docker-compose up -d api
```

### Access Swagger UI
**Interactive API docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📚 Additional Endpoints

- `GET /` - API status
- `GET /health` - Health check (Qdrant, LLM, Reranker status)
- `GET /documents` - List all indexed documents
