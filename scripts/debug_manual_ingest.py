import asyncio
import os
import sys
import yaml
from dotenv import load_dotenv
import nest_asyncio

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Load Env
load_dotenv(dotenv_path="config/.env")
nest_asyncio.apply()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

async def manual_run():
    print("🚀 STARTING MANUAL INGESTION...")
    
    config = load_config()
    
    # 1. Ingest
    ingestion = DocumentIngestion(config)
    chunks = await ingestion.ingest_documents()
    
    if not chunks:
        print("⚠️  No new chunks returned. (Did you reset processed_files.json?)")
        return

    print(f"✅ Generated {len(chunks)} Chunks.")

    # 2. Store
    print("💾 Saving to Qdrant...")
    retrieval = RetrievalService(config)
    retrieval.add_documents(chunks)
    
    print("✅ SAVED SUCCESSFULLY!")
    
    # 3. Verify
    print("🔍 Verifying Count...")
    db = retrieval.vector_store
    count = db._collection.count()
    print(f"📊 Total Vectors in DB: {count}")

if __name__ == "__main__":
    asyncio.run(manual_run())
