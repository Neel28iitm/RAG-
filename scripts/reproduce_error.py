
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("🚀 Reproducing Validation Error")
    config = load_config()
    retriever = RetrievalService(config)
    
    # Query that triggers the error (from user logs)
    query = "According to standard environmental noise reports (like the Mora case), what is the typical unit used to measure sound pressure levels at a facade?"
    
    print(f"❓ Query: {query}")
    
    try:
        docs = retriever.get_relevant_docs(query, top_k=5)
        print(f"✅ Retrieved {len(docs)} docs.")
        if len(docs) == 0:
            print("❌ Retrieved 0 docs (Error likely caught inside)")
    except Exception as e:
        print(f"❌ Outer Exception: {e}")

if __name__ == "__main__":
    main()
