# 📘 Final RAG Project Documentation (Hinglish)

Ye document poore project ka detailed breakdown hai. Isme humne har ek step ko explain kiya hai ki **kya use hua hai**, **kaise kaam karta hai**, aur **kyun choose kiya gaya**.

---

## 🏗️ High-Level Architecture (Architecture Kya Hai?)

Humara system ek **Advanced RAG (Retrieval-Augmented Generation)** pipeline hai jo bade documents (PDFs) ko samajh kar accurate answers deta hai.

**Main Components:**
1.  **Ingestion Engine:** Documents ko padhna aur todna (LlamaParse + Gemini).
2.  **Storage Layer:** Data ko store karna (AWS S3 + Qdrant Cloud).
3.  **Retrieval Engine:** Sahi data dhundhna (Hybrid Search + Reranking).
4.  **Generation Engine:** Answer likhna (Gemini 2.5 Flash).
5.  **User Interface:** User se baat karna (Streamlit).

---

## 🛠️ Step-by-Step Breakdown

### 1️⃣ Step 1: Ingestion (Data Processing)
**Goal:** PDF files ko machine-readable format mein convert karna aur store karna.

*   **Technology Used:**
    *   **LlamaParse:** PDFs ko padhne ke liye. Humne isme **Vendor Multimodal Mode** on kiya hai, jo **Gemini 2.5 Flash** ka vision use karta hai tables aur charts ko samajhne ke liye.
    *   **Format:** Result **Markdown** format mein aata hai taaki headings aur structure preserve rahein.
    *   **Chunking (Data Todna):** Hum **Parent-Child Chunking** use kar rahe hain.
        *   **Parent Chunk:** 2000 tokens (Ye bada tukda hai context ke liye).
        *   **Child Chunk:** 400 tokens (Ye chota tukda hai search ke liye).
    *   **Logic:** Chote chunks (Children) search karne mein aasaan hote hain, par jab answer dena hota hai to hum uska bada version (Parent) uthate hain taaki poora context mile.

### 2️⃣ Step 2: Storage (Data Rakhna)
**Goal:** Processed data ko secure aur fast access jagah pe rakhna.

*   **Technology Used:**
    *   **AWS S3:** Yahan humare **Parent Documents** (bade chunks) store hote hain.
        *   *Kyun?* Database ko heavy text se bachane ke liye.
    *   **Qdrant Cloud:** Yahan humare **Child Chunks (Vectors)** store hote hain.
        *   *Collection Name:* `rag_production`
        *   *Hosting:* GCP (Google Cloud) via Qdrant Cloud.
    *   **Queue System:** **Celery + Redis** use kiya hai taaki agar 100 files bhi upload karo to wo background mein process ho, UI hang na ho.

### 3️⃣ Step 3: Retrieval (Data Dhundna)
**Goal:** User ke sawal ka sabse relevant jawab dhundhna.

*   **Technology Used:**
    *   **Embedding Model:** `models/text-embedding-004` (Google ka latest embedding model).
    *   **Hybrid Search:** Hum do tarah se search karte hain:
        1.  **Dense Vector Search:** Meaning samajh kar dhundna (Semantic search).
        2.  **Sparse Search (BM25):** Keywords match karna (Exact match).
    *   **Query Rewriting:** User ka sawal seedha database mein nahi jaata. Pehle **Gemini 2.5 Flash** usse "Rewrite" karta hai taaki technical terms sahi ho jayein.
        *   *Example:* User bola "noise limit", Agent ne banaya "standard environmental noise limits db(A)".
    *   **Reranking:** **FlashRank** use kiya hai.
        *   Iska kaam hai top 60 results ko dobara check karna aur best 5 ko upar lana.

### 4️⃣ Step 4: Generation (Answer Banana)
**Goal:** Dhunde huye data se insani bhasha mein jawab dena.

*   **Technology Used:**
    *   **LLM:** **Gemini 2.5 Flash**.
        *   *Kyun?* Ye fast hai, cheap hai aur long context samajhta hai.
    *   **System Prompt:** Humne ek "Universal AI Analyst" persona banaya hai.
        *   **Language Rule:** Agar user Hindi mein puche, to Hindi mein jawab do.
        *   **Citation Rule:** Har jawab ke end mein source file ka naam batana zaroori hai.

### 5️⃣ Step 5: User Interface (UI) in Streamlit
**Goal:** User ko easy experience dena.

*   **Features:**
    *   **Chat History:** Purani baatein yaad rakhne ke liye session state aur local DB (`rag_app.db`) use kiya hai.
    *   **Admin Dashboard:** Sidebar mein dikhta hai ki kitni files process ho gayi hain (Status: DONE/FAILED).

---

## ⚙️ Configuration Summary (`settings.yaml`)

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **LLM Model** | `gemini-2.5-flash` | Main brain of the system. |
| **Embedding** | `text-embedding-004` | Data ko numbers mein convert karne ke liye. |
| **Parent Chunk** | 2000 chars | Answer generation ke liye context size. |
| **Child Chunk** | 400 chars | Searching ke liye small packet size. |
| **Retrieval Top-K** | 5 | Final user ko 5 best documents dikhenge. |
| **Reranking Candidates** | 60 | Pehle 60 documents laye jate hain, fir filter hote hain. |

---

## 🚀 Deployment Info
*   **Infrastructure:** Dockerized (Docker Compose).
*   **Services:**
    1.  `app`: Main Streamlit Application.
    2.  `worker`: Celery Worker (Upload processing).
    3.  `redis`: Queue Broker.
*   **Cloud:** Qdrant Cloud (Vector DB) & AWS S3 (File Storage).

---
*Created by Antigravity Agent - 18 Jan 2026*
