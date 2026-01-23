
import os
import sys
from qdrant_client import QdrantClient, models

# Add src to path
sys.path.append(os.getcwd())

from src.core.config import load_config, load_env_robust
from src.core.vector_store import get_qdrant_client

# Load Env
load_env_robust()
config = load_config("config/settings.yaml")

def fix_index():
    print("🚀 Connecting to Qdrant...")
    client = get_qdrant_client(config)
    collection_name = config['paths']['vector_store_config']['collection_name']
    
    print(f"🔧 Creating Keyword Index for 'metadata.source' in collection: {collection_name}")
    
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.source",
            field_schema=models.PayloadSchemaType.TEXT
        )
        print("✅ Index Creation Triggered successfully.")
    except Exception as e:
        print(f"❌ Failed to create index (might already exist): {e}")

    # Also index 'page_label' just in case
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.page_label",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        print("✅ 'page_label' Index Creation Triggered.")
    except Exception:
        pass

if __name__ == "__main__":
    fix_index()
