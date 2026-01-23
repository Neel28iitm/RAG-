
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService

load_dotenv("config/.env")
load_dotenv(".env")

async def main():
    print("🤖 Simulating Full RAG Response...")
    config = load_config()
    
    # Initialize Services
    retrieval_service = RetrievalService(config)
    generation_service = GenerationService(config)
    
    query = "What was the measured sound level at the facade when five waxing stations were forced?"
    print(f"❓ User Query: {query}")
    
    # 1. Retrieve
    print("🔍 Retrieving Documents...")
    docs = retrieval_service.get_relevant_docs(query, top_k=5)
    
    if not docs:
        print("❌ No documents retrieved.")
        return

    print(f"✅ Retrieved {len(docs)} documents.")
    print("   Top Source:", docs[0].metadata.get('source'))
    
    # 2. Generate
    print("🧠 Generating Answer...")
    # Mocking chat history as empty for this test
    answer = generation_service.generate_answer(query, docs, chat_history=[])
    
    print("\n" + "="*50)
    print("📝 FINAL ANSWER:")
    print("="*50)
    print(answer)
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
