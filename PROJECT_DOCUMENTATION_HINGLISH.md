# 📘 RAG Project End-to-End Documentation (Hinglish)

Yeh document aapko is RAG (Retrieval Augmented Generation) project ko samajhne, setup karne aur chalane mein madad karega. Yahan har step ko start se lekar end tak detail mein samjhaya gaya hai.

---

## 🏗️ 1. Project Parichay (Introduction)
Yeh project ek **Production-Ready RAG System** hai. Iska main kaam hai users ko apne documents (PDFs) se baat karne ki suvidha dena. 

**Kyu banaya gaya hai?**
Normal LLMs (jaise ChatGPT) ko aapke private data ka pata nahi hota. Yeh system aapke private data (PDFs) ko padhta hai, samajhta hai, aur jab aap sawal puchte hain, toh sirf relevant information nikal kar jawab deta hai.

### ✨ Key Features (Khasiyat)
- **Hybrid Search**: Keyword (BM25) aur Meaning (Vector) dono ka use karta hai best results ke liye.
- **Parent-Child Retrieval**: Bade documents ko chote chunks mein todta hai par answer dete waqt pura context use karta hai.
- **Asynchronous Ingestion**: Background mein files process hoti hain bina app ko slow kiye.
- **Scalable**: Docker, Redis aur Celery ka use kiya gaya hai taaki heavy load handle kar sake.

---

## 🛠️ 2. Takneek (Tech Stack)
Is project mein best-in-class tools use kiye gaye hain:

| Component | Tool Used | Kaam kya karta hai? |
|-----------|-----------|---------------------|
| **Language** | Python 3.9+ | Main coding language. |
| **LLM** | Gemini 2.5 Flash | Sawaalo ke jawab generate karne ke liye. |
| **Embeddings** | Google Generative AI (004) | Text ko numbers (vectors) mein convert karne ke liye. |
| **Vector DB** | Qdrant | Vectors ko store aur search karne ke liye. |
| **Queue/Broker** | Redis | Tasks ko manage karne ke liye. |
| **Worker** | Celery | Background mein bhaari kaam (ingestion) karne ke liye. |
| **Frontend** | Streamlit | User interface jahan aap chat karte hain. |
| **Storage** | AWS S3 | Raw PDF files aur Parent Documents store karne ke liye. |
| **Parsing** | LlamaParse | PDF se text nikalne ke liye (Vendor Multimodal mode). |

---

## 📂 3. Folder Folder ka Dhancha (Project Structure)
Project ki files is tarah organized hain:

```
RAG_PROJECT/
├── config/                 # Settings aur configurations
│   └── settings.yaml       # Model names, chunk sizes, DB URL lay
├── data/                   # Local data storage (agar chahiye)
├── logs/                   # Error aur Info logs
├── scripts/                # Utility scripts (Deployment, Debugging)
├── src/                    # Main Source Code
│   ├── app/                # Core Application Logic
│   │   ├── ingestion.py    # PDF processing aur indexing
│   │   ├── retrieval.py    # Search aur finding logic
│   │   ├── generation.py   # LLM answer generation
│   │   ├── history.py      # Chat history maintain karna
│   │   └── embedding.py    # Embedding models wrapper
│   ├── core/               # Database aur Config management
│   ├── worker/             # Celery tasks (Background processing)
│   └── streamlit_app.py    # UI Code
├── docker-compose.yml      # Docker services definition
├── Dockerfile              # App image definition
├── docker-compose.yml      # Docker services definition
├── Dockerfile              # App image definition
├── api_handover.py         # FastAPI Backend Entry Point
├── main.py                 # Streamlit Frontend Entry Point
└── requirements.txt        # Python libraries list
```

---

## 🚀 4. Setup aur Installation (Shuruat kaise kare)

### Step 1: Prerequisites (Zaroori Cheezein)
Aapke system mein yeh install hona chahiye:
- **Docker Desktop**: Containers chalane ke liye.
- **Python 3.10+**: Agar local run karna ho.
- **Git**: Code download karne ke liye.

### Step 2: Environment Variables (.env) setup karein
Project root mein ek `.env` file banayein aur yeh details bharein:

```ini
# API Keys
GOOGLE_API_KEY=your_google_api_key_here
COHERE_API_KEY=your_cohere_key_if_used

# AWS S3 Config (Files storage ke liye)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=neel-rag-data-2026

# Database Config
QDRANT_URL=https://<your-cluster>.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=your_cloud_api_key

# Redis (Local Docker ke liye)
REDIS_URL=redis://redis:6379/0
```

### Step 3: Application Run karein (Docker ke saath)
Sabse aasaan tarika hai Docker use karna. Terminal open karein aur type karein:
```bash
docker-compose up --build
```
Isse 5 services start hongi:
1. **Redis**: Messaging ke liye.
2. **Qdrant**: Vector Database (MIGRATED TO CLOUD).
3. **Worker**: Background tasks processing ingestions.
4. **API**: Backend Logic (FastAPI on port 8000).
5. **App**: Frontend UI (Streamlit on port 8501).

Jab sab chal jaye:
- **Frontend (UI)**: Browser mein kholein `http://localhost:8501`
- **Backend (API)**: `http://localhost:8000/docs` (Swagger UI)

---

## ⚙️ 5. Vistar mein Workflow (Detailed Workflow)

### A. Ingestion Flow (Data kaise system mein aata hai)
Jab aap koi PDF file system mein daalte hain (S3 bucket mein), toh yeh process hota hai:

1. **Detection**: `ingestion.py` S3 bucket scan karta hai new PDFs ke liye.
2. **Queueing**: Agar nayi file milti hai, toh uska naam **Redis** queue mein daal diya jaata hai.
3. **Processing (Worker)**: **Celery Worker** task uthata hai aur `DocumentIngestion` class ko call karta hai.
4. **Parsing**: **LlamaParse** file ko padhta hai. Isme ek **Fallback Mechanism** hai:
    - **Primary**: Vendor Multimodal Mode try karta hai (best for complex PDFs).
    - **Fallback**: Agar woh fail ho jaye (empty content), toh automatically Standard Text Mode par switch karta hai taaki data loss na ho.
5. **Chunking**: Text ko chote tukdon (Parent Chunks) mein baanta jaata hai.
6. **Indexing**: 
    - **Parent Docs**: Pura content S3 `parent_store/` mein save hota hai.
    - **Child Processing**: Parent chunks ko aur chota karke (Child Chunks) **Qdrant** vector store mein daala jaata hai taaki searching fast ho.
7. **Status Update**: Database mein file ka status "COMPLETED" mark kar diya jaata hai.

### B. Retrieval Flow (Jawab kaise dhundha jaata hai)
Jab user sawal puchta hai:

1. **Query Processing**: User ka sawal `retrieval.py` ke paas jaata hai.
2. **Hybrid Search**: Query ko vector mein convert karke Qdrant mein search kiya jaata hai (Semantic search) aur saath hi keywords match (BM25) bhi dekha jaata hai.
3. **Parent Fetching**: Jo chote (child) chunks match hote hain, unke **Parent Documents** (original bada context) ko S3 se fetch kiya jaata hai using `ParentDocumentRetriever`.
4. **Reranking**: `FlashRank` use karke results ko dubara rank kiya jaata hai taaki sabse accurate result top par aayen.

### C. Generation Flow (AI Jawab kaise banata hai)
1. **Context Assembly**: Retrieval se mile Top-K (eg. 20) documents ko ek saath joda jaata hai.
2. **LLM Prompting**: Gemini 2.5 Flash ko ek prompt bheja jaata hai: 
   *"Yeh context hai, aur yeh user ka sawal hai. Context ke base par jawab do."*
3. **Response**: AI jawab stream karta hai jo `streamlit_app.py` par dikhta hai. Chat history `history.py` manage karta hai taaki purani baatein yaad rahein.

---

## 🐛 6. Common Issues & Debugging (Aam Samasyaein)

1. **Ingestion ruk gayi / Files process nahi ho rahi?**
   - Check karein Worker chal raha hai ya nahi. Docker logs dekhein:
     `docker-compose logs -f worker`
   - Agar Redis connect nahi ho raha, toh `.env` mein `REDIS_URL` check karein.

2. **Jawab galat aa raha hai?**
   - `config/settings.yaml` mein `retrieval.top_k` badhayein (abhi 20 hai).
   - Check karein ki document sahi se parse hua hai ya nahi (logs mein "Processing...").

3. **Streamlit open nahi ho raha?**
   - Check karein port `8501` access kar rahe hain (pehle 8000 tha, ab change ho gaya hai).
   - Browser mein `http://localhost:8501` open karein.

4. **"Connection Refused" error aa raha hai?**
   - Yeh tab hota hai jab Docker container `localhost` par connect karne ki koshish karta hai.
   - Make sure karein `docker-compose.yml` mein `QDRANT_URL=http://qdrant:6333` set hai (na ki localhost).

---
**Summary**: Yeh project ek robust architecture follow karta hai jo bade scale par bhi chal sakta hai. Agar aapko koi naya feature add karna hai, toh `src/app` mein changes karein.
