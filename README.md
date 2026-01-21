# RAG Production System

Production-ready Retrieval-Augmented Generation (RAG) system with advanced PDF processing, hybrid search, and multilingual support.

## 🚀 Features

- **Advanced PDF Processing**: LlamaParse with Gemini 2.5 Flash multimodal parsing
- **Auto-Rotation Fix**: Free PyMuPDF-based rotation detection and correction
- **Hybrid Search**: Dense (text-embedding-004) + Sparse (BM25) retrieval
- **Multilingual Reranking**: Cohere rerank-multilingual-v3.0
- **Parent-Document Retrieval**: Optimized for tables and long-form content
- **Production-Ready**: Celery workers, Redis caching, PostgreSQL tracking

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

## 🔍 Monitoring

### Check Processing Status

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
