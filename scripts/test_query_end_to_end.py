
import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService

# Load Env
load_dotenv("config/.env")
# Also load root .env if needed
load_dotenv(".env")

async def main():
    print("🧪 Starting Query Test...")
    config = load_config()
    
    # 1. Test Retrieval
    print("\n🔍 Testing Retrieval...")
    try:
        retriever = RetrievalService(config)
        query = "What represents the sound insulation?" 
        docs = retriever.get_relevant_docs(query)
        print(f"✅ Retrieved {len(docs)} documents.")
        for i, doc in enumerate(docs[:2]):
            print(f"   Doc {i+1}: {doc.metadata.get('source', 'Unknown')} (Length: {len(doc.page_content)})")
    except Exception as e:
        print(f"❌ Retrieval Failed: {e}")
        return

    # 2. Test Generation
    print("\n🤖 Testing Generation...")
    try:
        generator = GenerationService(config)
        # Mock chat history
        chat_history = []
        answer = generator.generate_answer(query, docs, chat_history)
        print(f"✅ Answer Generated:\n{answer}")
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        return

    print("\n🎉 System is READY!")

if __name__ == "__main__":
    asyncio.run(main())
