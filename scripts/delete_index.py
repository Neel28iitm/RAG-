
import os
import sys
import time
from qdrant_client import QdrantClient

sys.path.append(os.getcwd())
from src.core.config import load_config, load_env_robust
from src.core.vector_store import get_qdrant_client

load_env_robust()
config = load_config("config/settings.yaml")

def delete_idx():
    print("🚀 Connecting to Qdrant...")
    client = get_qdrant_client(config)
    collection_name = config['paths']['vector_store_config']['collection_name']
    
    print(f"🗑️ Deleting Index for 'metadata.source'...")
    try:
        client.delete_payload_index(collection_name, "metadata.source")
        print("✅ Delete triggered successfully.")
    except Exception as e:
        print(f"⚠️ Delete failed: {e}")

if __name__ == "__main__":
    delete_idx()
