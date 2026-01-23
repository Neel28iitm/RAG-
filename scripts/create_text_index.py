
import os
import sys
from qdrant_client import QdrantClient, models

sys.path.append(os.getcwd())
from src.core.config import load_config, load_env_robust
from src.core.vector_store import get_qdrant_client

load_env_robust()
config = load_config("config/settings.yaml")

def create_text_idx():
    print("🚀 Connecting to Qdrant...")
    client = get_qdrant_client(config)
    collection_name = config['paths']['vector_store_config']['collection_name']
    
    print(f"🔧 Creating TEXT Index for 'metadata.source'...")
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.source",
            field_schema=models.PayloadSchemaType.TEXT
        )
        print("✅ TEXT Index Creation Triggered.")
    except Exception as e:
        print(f"❌ Create failed: {e}")

if __name__ == "__main__":
    create_text_idx()
