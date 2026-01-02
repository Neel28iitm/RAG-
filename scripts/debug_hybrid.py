
import sys
import os
import asyncio
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.utils import setup_logger

# Load env
load_dotenv("config/.env")
logger = setup_logger('debug_hybrid')

def main():
    config = load_config()
    print("🚀 Initializing Retrieval Service (Hybrid Mode)...")
    try:
        retrieval_service = RetrievalService(config)
    except Exception as e:
        print(f"❌ Failed to init service: {e}")
        return

    # User's query causing issues
    query = "According to the section on isolation measures, how much noise level reduction (in dB) can typically be achieved in the medium to high-frequency range by using a 'double-elastic mounting' (doppelt-elastische Aufstellung)?"
    
    print(f"\n❓ Query: {query}")
    
    # 1. Test Raw Search (LangChain Wrapper)
    print("\n🔍 Testing Raw Qdrant Search (Hybrid)...")
    try:
        vs = retrieval_service.vector_store
        print(f"👉 Vector Store Type: {type(vs)}")
        if vs is None:
            print("❌ Vector Store is NONE! Initialization failed silentlly?")
            return

        # We access the internal vector store to see what it returns before re-ranking
        docs = vs.similarity_search(query, k=5)
        print(f"✅ Found {len(docs)} documents via Raw Search.")
        for i, doc in enumerate(docs):
            print(f"   [{i+1}] Source: {doc.metadata.get('source')} | Preview: {doc.page_content[:100]}...")
    except Exception as e:
        print(f"❌ Raw Search Failed: {e}")

    # 2. Test Full Pipeline (with Re-ranking)
    print("\n🔄 Testing Full Pipeline (Get Relevant Docs)...")
    try:
        final_docs = retrieval_service.get_relevant_docs(query)
        if not final_docs:
            print("❌ Pipeline returned NO documents.")
        else:
            print(f"✅ Pipeline returned {len(final_docs)} documents.")
            for i, doc in enumerate(final_docs):
                print(f"   [{i+1}] {doc.page_content[:150]}...")
                
    except Exception as e:
        print(f"❌ Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
