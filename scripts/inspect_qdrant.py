
import os
import sys
import yaml
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv("config/.env")

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    qdrant_url = config['paths']['vector_store_config']['url']
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
    except Exception as e:
        print(f"❌ Failed to get info: {e}")

if __name__ == "__main__":
    main()
