
import asyncio
import os
import sys
import sys
from dotenv import load_dotenv

# Force UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("🚀 Minimal Retrieval Test")
    config = load_config()
    retriever = RetrievalService(config)
    print("🚀 Minimal Retrieval Test")
    
    query = "vallastation"
    print(f"❓ Query: {query}")
    print("running similarity_search directly on vector_store...")
    
    # Bypass get_relevant_docs logic (which has Rewriter + Ranker)
    try:
        # Use underlying QdrantVectorStore search which uses 'similarity_search'
        docs = retriever.vector_store.similarity_search(query, k=5)
        print(f"✅ vector_store.similarity_search found {len(docs)} docs.")
        for d in docs:
            print(f" - {d.metadata.get('source')} | Content: {d.page_content[:50]}...")
            
    except Exception as e:
        print(f"❌ Search Failed: {e}")

if __name__ == "__main__":
    main()
