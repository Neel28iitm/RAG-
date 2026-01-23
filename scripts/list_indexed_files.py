
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load envs
load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("📊 Listing Indexed Files in Qdrant...")
    
    url = os.getenv("QDRANT_URL")
    key = os.getenv("QDRANT_API_KEY")
    collection_name = "rag_production"
    
    if not url:
        print("❌ QDRANT_URL not found!")
        return

    client = QdrantClient(url=url, api_key=key)
    
    # Scroll to get all unique sources
    unique_sources = set()
    next_offset = None
    total_scanned = 0
    
    print("🔄 Scanning vectors (this might take a moment)...")
    
    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=next_offset,
            with_payload=True,
            with_vectors=False
        )
        
        for point in points:
            payload = point.payload or {}
            # Metadata might be nested or flat depending on ingestion
            meta = payload.get('metadata', {})
            # Try getting source from payload root or metadata dict
            src = payload.get('source') or meta.get('source') or "Unknown"
            
            # Clean up filename if it's a path
            src = os.path.basename(src)
            unique_sources.add(src)
            
        total_scanned += len(points)
        # print(f"   Scanned {total_scanned} points...", end='\r')
        
        if next_offset is None:
            break
            
    print(f"\n✅ Scan Complete. Total Vectors Checked: {total_scanned}")
    print(f"📂 Total Unique PDF Files: {len(unique_sources)}")
    print("-" * 40)
    for i, src in enumerate(sorted(unique_sources), 1):
        print(f"{i}. {src}")
    print("-" * 40)

if __name__ == "__main__":
    main()
