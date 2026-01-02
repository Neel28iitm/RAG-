import asyncio
import os
import logging
from dotenv import load_dotenv
from src.app.ingestion import DocumentIngestion
import nest_asyncio
import yaml

nest_asyncio.apply()
load_dotenv(dotenv_path="config/.env")

# Setup logging to console
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

async def debug_run():
    config = load_config()
    ingestion = DocumentIngestion(config)
    
    print("="*50)
    print("DEBUG INGESTION START")
    print("="*50)
    
    files = list(ingestion.data_raw.glob("*.pdf"))
    print(f"Found {len(files)} PDFs in {ingestion.data_raw}")
    
    for f in files:
        print(f"Processing: {f.name}")
        chunks = await ingestion.process_file(f)
        print(f"Result Chunks: {len(chunks)}")
        if len(chunks) == 0:
            print("❌ ZERO CHUNKS RETURNED! Checking why...")
            # We can't easily check inside the class instance without modifying it, 
            # but the logs from 'app_logger' should show errors if we configured logging right.
        else:
            print("✅ Chunking Succeeded")
            print(f"Sample Content: {chunks[0].page_content[:100]}...")

if __name__ == "__main__":
    asyncio.run(debug_run())
