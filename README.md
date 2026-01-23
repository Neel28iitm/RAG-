# RAG Production System

Production-ready Retrieval-Augmented Generation (RAG) system with advanced PDF processing, hybrid search, and multilingual support.

## 🚀 Features

- **Advanced PDF Processing**: LlamaParse with Gemini 2.5 Flash multimodal parsing
- **Auto-Rotation Fix**: Free PyMuPDF-based rotation detection and correction
- **Hybrid Search**: Dense (text-embedding-004) + Sparse (BM25) retrieval
- **Multilingual Reranking**: Cohere rerank-multilingual-v3.0
- **Parent-Document Retrieval**: Optimized for tables and long-form content
- **Production-Ready**: Celery workers, Redis caching, PostgreSQL tracking

## 💻 System Requirements

### Ubuntu/Debian Setup
Before running the app, you must install Redis Server (critical for the Celery worker queue):
```bash
sudo apt update
sudo apt install redis-server -y
```

### AWS Setup
For EC2 deployments, it is highly recommended to use an IAM Role instead of hardcoded keys:
- **IAM Role**: Attach an IAM Role with `AmazonS3FullAccess` to your EC2 instance.
- This allows the app to authenticate automatically without needing `AWS_ACCESS_KEY_ID` in `.env`.

## 📋 Prerequisites

- Docker & Docker Compose
- AWS S3 bucket
- API Keys:
  - Google AI API Key
  - LlamaParse API Key
  - Cohere API Key

## ⚡ Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Neel28iitm/RAG-.git
cd RAG-
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Required API Keys:**
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`
- `GOOGLE_API_KEY`
- `LLAMA_CLOUD_API_KEY`
- `COHERE_API_KEY`
- `QDRANT_URL` & `QDRANT_API_KEY` (for Qdrant Cloud)

### 3. Start All Services

```bash
docker-compose up -d
```

### 4. Access Application

**🌐 Live Demo (Try Now!):**
- **Demo URL**: https://kason-scripless-bok.ngrok-free.dev
- Test the system without setup
- Note: This is a temporary demo instance

---

**Option A: Local Access**
- **Streamlit UI**: http://localhost:8501
- **Qdrant Dashboard**: http://localhost:6333/dashboard

**Option B: Public Access (ngrok)**
```bash
# Install ngrok (if not installed)
# Download from: https://ngrok.com/download

# Expose Streamlit on public URL
ngrok http 8501

# Share the generated URL (e.g., https://abc123.ngrok.io)
```

**Production Deployment:**
- For production, use proper reverse proxy (Nginx)
- Or deploy on cloud platforms (AWS ECS, Google Cloud Run, etc.)
- ngrok is great for testing/demos

## 📊 Architecture

```
┌─────────────┐
│  Streamlit  │  ← User Interface (Port 8501)
└──────┬──────┘
       │
┌──────▼──────────────────────────────────┐
│         Application Layer                │
│  • Ingestion (PDF Processing)            │
│  • Retrieval (Hybrid Search + Reranking) │
│  • Generation (LLM Answers)              │
└──────┬──────────────────────────────────┘
       │
┌──────▼──────┬────────────┬──────────────┐
│   Celery    │   Redis    │  PostgreSQL  │
│   Worker    │   Cache    │  FileTracking│
└─────────────┴────────────┴──────────────┘
       │
┌──────▼──────┬──────────────────┐
│   Qdrant    │     AWS S3       │
│  Vectors    │  Document Store  │
└─────────────┴──────────────────┘
```

## 🔧 Services

| Service | Port | Purpose |
|---------|------|---------|
| Streamlit | 8501 | Web UI |
| Qdrant | 6333 | Vector database |
| PostgreSQL | 5432 | File tracking |
| Redis | 6379 | Cache + Queue |

## 📁 Project Structure

```
src/
├── app/
│   ├── ingestion.py      # PDF processing pipeline
│   ├── retrieval.py      # Hybrid search + reranking
│   ├── generation.py     # LLM answer generation
│   └── embedding.py      # Google embeddings
├── core/
│   ├── config.py         # Configuration loader
│   ├── database.py       # PostgreSQL connection
│   ├── models.py         # FileTracking model
│   └── vector_store.py   # Qdrant client
├── worker/
│   ├── celery_app.py     # Celery configuration
│   └── tasks.py          # Background tasks
└── streamlit_app.py      # Main UI application
```

## 🎯 Usage

### Upload Documents

1. Upload PDFs to S3: `s3://your-bucket/raw/`
2. Navigate to Streamlit UI
3. Click "Trigger Ingestion"
4. Monitor progress in FileTracking

### Query Documents

1. Open Streamlit UI
2. Enter your question
3. Get AI-powered answers with citations

## 💰 Cost Optimization

**Stay within free tier:**
- LlamaParse: 1,000 pages/day FREE
- Process ≤10 documents/day (100 pages each)
- **Monthly cost: $0** ✅

**Paid usage:**
- $0.30 per 100-page document
- $0.0007 per query

## 🔍 Monitoring & Health Checks

### System Health Dashboard

```bash
# Run comprehensive health check
python scripts/trace_dashboard.py
```

This will verify:
- ✅ Environment variables (API keys)
- ✅ Qdrant connectivity
- ✅ S3 access
- ✅ Database integrity
- ✅ Vector-to-S3 consistency

**Output:** `trace_report.txt` with full system health status

### Quick Status Check

```bash
# Check document processing status
python scripts/check_status.py
```

Shows:
- Total files in database
- Completed/Failed/Processing counts
- Recent errors

### Check Processing Status (Database)

```bash
docker exec rag_postgres psql -U rag_user -d rag_db -c "SELECT filename, status FROM file_tracking;"
```

### View Worker Logs

```bash
docker logs -f rag_celery_worker
```

### Qdrant Collection Stats

```bash
curl http://localhost:6333/collections/rag_production
```

## 🔌 Backend API Integration

**Note for Developers:** The core backend (`src/app/`) is **completely decoupled** from Streamlit. You can integrate it into any framework.

### FastAPI Integration Example

```python
from fastapi import FastAPI
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.config import load_config

app = FastAPI()
config = load_config()

retrieval = RetrievalService(config)
generation = GenerationService(config)

@app.post("/chat")
def chat(query: str):
    # Retrieve relevant documents
    docs, metrics = retrieval.get_relevant_docs(query, top_k=10)
    
    # Generate answer
    answer = generation.generate_answer(query, docs)
    
    return {
        "answer": answer,
        "sources": [d.metadata for d in docs],
        "metrics": metrics
    }
```

### Key Services

| Service | File | Purpose |
|---------|------|---------|
| **Ingestion** | `src/app/ingestion.py` | PDF → Chunks |
| **Retrieval** | `src/app/retrieval.py` | Hybrid Search + Reranking |
| **Generation** | `src/app/generation.py` | LLM Answer Generation |
| **Embedding** | `src/app/embedding.py` | Text → Vectors |

All services are **Streamlit-independent** and ready for API wrapping.

## 🛠️ Troubleshooting

### Worker Not Processing

```bash
docker restart rag_celery_worker
docker logs -f rag_celery_worker
```

### Database Connection Issues

```bash
docker exec -it rag_postgres psql -U rag_user -d rag_db
```

### Fresh Start (Clear All Data)

```bash
docker-compose down -v
docker-compose up -d
```

## 🔒 Security

- API keys stored in `.env` file (NOT committed to Git)
- PostgreSQL password configurable
- S3 IAM permissions recommended

## 📈 Performance

- **Ingestion**: ~45s per 100-page PDF
- **Retrieval**: <3s (includes reranking)
- **Generation**: Streaming responses

## 🌍 Language Support

- Multilingual parsing (English, German, Swedish)
- Multilingual reranking (Cohere)
- Context-aware query rewriting

## 🎓 Advanced Features

- **Rotation Auto-Fix**: PyMuPDF-based (FREE)
- **Quality Validation**: Encoding checks
- **Parent-Document Retrieval**: 5000-char parents, 600-char children
- **Metadata Enrichment**: Timestamps, parsing methods, rotation flags
- **Atomic Operations**: Race condition protection
- **S3 Retry Logic**: Network failure handling

## 📝 Development

### Local Setup (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start services manually
redis-server &
qdrant --path ./qdrant_storage &

# Start worker
celery -A src.worker.celery_app worker --loglevel=info

# Start Streamlit
streamlit run src/streamlit_app.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

[Add your license here]

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Contact: [Your email]

## 🙏 Acknowledgments

- LlamaParse for PDF processing
- Google AI for embeddings and generation
- Cohere for multilingual reranking
- Qdrant for vector storage

---

**Built with ❤️ for production deployment**
