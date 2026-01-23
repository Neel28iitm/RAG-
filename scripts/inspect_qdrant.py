
import os
import sys
import yaml
from qdrant_client import QdrantClient

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import load_env_robust

load_env_robust("config/.env")
load_env_robust(".env")

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    qdrant_url = os.getenv("QDRANT_URL", config['paths']['vector_store_config']['url'])
    collection_name = config['paths']['vector_store_config']['collection_name']
    api_key = os.getenv("QDRANT_API_KEY")

    print(f"🕵️ Inspecting Collection: {collection_name}")
    
    if "http" in qdrant_url or "localhost" in qdrant_url:
         client = QdrantClient(url=qdrant_url, api_key=api_key)
    else:
         client = QdrantClient(path=qdrant_url)

    try:
        info = client.get_collection(collection_name)
        print(f"✅ Collection found!")
        print(f"   Vectors Config: {info.config.params.vectors}")
        print(f"   Sparse Vectors Config: {info.config.params.sparse_vectors}")
        print(f"   📊 Total Points (Vectors): {info.points_count}")
        print(f"   Indexed Vectors Count: {info.vectors_count}")
    except Exception as e:
        print(f"❌ Failed to get info: {e}")

if __name__ == "__main__":
    main()
