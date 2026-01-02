
import os
import sys
import yaml
from qdrant_client import QdrantClient, models
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

    print(f"🚀 Deploying Hybrid Schema for: {collection_name}")
    
    if "http" in qdrant_url or "localhost" in qdrant_url:
         client = QdrantClient(url=qdrant_url, api_key=api_key)
    else:
         client = QdrantClient(path=qdrant_url)

    # 1. Delete if exists
    try:
        client.delete_collection(collection_name)
        print("🗑️  Deleted old collection.")
    except:
        pass

    # 2. Create with Explicit Hybrid Config
    # Dense Vector: "content" (Default in LangChain Qdrant is None or 'content'?)
    # LangChain Qdrant defaults:
    # - If vector_name is None -> uses root vector (empty name).
    # - If sparse_vector_name is None -> uses 'langchain-sparse'?
    
    # We will create root dense vector + named sparse vector.
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=768, # Gemini Embedding Dimension
            distance=models.Distance.COSINE
        ),
        sparse_vectors_config={
            "langchain-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False,
                )
            )
        }
    )
    
    print("✅ Created Collection with Hybrid Schema (Dense: 768, Sparse: langchain-sparse)")

if __name__ == "__main__":
    main()
