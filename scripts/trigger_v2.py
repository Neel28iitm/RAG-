
import sys
import os
import asyncio
import logging
# Manual Env Loading
def load_env_manual(path):
    import os
    try:
        # Try UTF-8 first
        try:
             content = open(path, 'r', encoding='utf-8').read()
        except UnicodeError:
             # Fallback to UTF-16
             content = open(path, 'r', encoding='utf-16').read()
             
        for line in content.splitlines():
             line = line.strip()
             if not line or line.startswith('#'): continue
             if '=' in line:
                 key, val = line.split('=', 1)
                 val = val.strip().strip("'").strip('"')
                 os.environ[key.strip()] = val
    except Exception as e:
        print(f"Failed to load {path}: {e}")

load_env_manual(".env")

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.core.database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def trigger_ingestion():
    # Initialize DB
    init_db()
    
    # Load settings
    config = load_config("config/settings.yaml")
    
    # Init Ingestor
    ingestor = DocumentIngestion(config)
    print("🚀 Triggering S3 Ingestion Scan (V2)...")
    
    # Run
    await ingestor.ingest_documents()
    print("✅ Scan Complete.")

if __name__ == "__main__":
    asyncio.run(trigger_ingestion())
