
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("🛠️ Creating Index on 'metadata.source'...")
    
    url = os.getenv("QDRANT_URL")
    key = os.getenv("QDRANT_API_KEY")
    collection_name = "rag_production"
    
    if not url:
        print("❌ QDRANT_URL not found!")
        return

    client = QdrantClient(url=url, api_key=key)
    
    try:
        # Create Payload Index for Text Matching
        client.create_payload_index(
            collection_name=collection_name,
            field_name="metadata.source",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=15,
                lowercase=True
            )
        )
        print("✅ Index Creation Triggered. Waiting for it to finish...")
        
        # Wait? Usually fast.
        print("✅ Done.")
        
    except Exception as e:
        print(f"❌ Index Creation Failed: {e}")

if __name__ == "__main__":
    main()
