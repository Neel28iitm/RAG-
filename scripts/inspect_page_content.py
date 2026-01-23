
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path

# Load env
env_path = Path('config/.env')
load_dotenv(env_path)

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

def inspect_page(page_num):
    print(f"🔍 Searching for Page {page_num} content...")
    # Fetch all chunks for the file (using indexed metadata.source)
    chunks = []
    next_page_offset = None
    while True:
        results, next_page_offset = client.scroll(
            collection_name='rag_production',
            scroll_filter={
                'must': [
                    {'key': 'metadata.source', 'match': {'value': 'Taschenbuch der Technischen Akustik - Lärmbekämpfung auf Schiffen.pdf'}}
                ]
            },
            limit=100,
            offset=next_page_offset,
            with_payload=True
        )
        chunks.extend(results)
        if next_page_offset is None:
            break
            
    print(f"📦 Scanned {len(chunks)} total chunks.")
    
    print(f"📦 Scanned {len(chunks)} total chunks.")
    
    print("🔍 Sampling Metadata & Content Markers:")
    for i, hit in enumerate(chunks):
        meta = hit.payload.get('metadata', {})
        page_label = meta.get('page_label', 'N/A')
        
        if 'vision_error' in meta:
            print(f"⚠️ FOUND VISION ERROR in Chunk {i} (Page {page_label}): {meta['vision_error']}")
        
        if 'vision_enhanced' in meta:
            print(f"✅ FOUND VISION ENHANCED FLAG in Chunk {i} (Page {page_label})")

    vision_chunks = []
    for hit in chunks:
        content = hit.payload.get('page_content', hit.payload.get('text', ''))
        meta = hit.payload.get('metadata', {})
        header_3 = meta.get('Header 3', '')
        
        # Check Header 3 for Vision marker (consumed by splitter)
        if "Vision Extraction" in header_3:
            vision_chunks.append((content, header_3))
        # Fallback: check content just in case
        elif "Enhanced Vision Extraction" in content:
            vision_chunks.append((content, "In-Content"))

    if vision_chunks:
        print(f"✅ FOUND {len(vision_chunks)} CHUNKS WITH VISION DATA!")
        for i, (content, h3) in enumerate(vision_chunks):
            print(f"\n--- VISION DATA CHUNK {i+1} (Header 3: {h3}) ---")
            print(content[:2000]) # Print start of chunk
            if "Wohnraum" in content:
                print("⭐ 'Wohnraum' FOUND IN THIS CHUNK!")
            else:
                print("⚠️ 'Wohnraum' NOT found in this chunk.")
    else:
        print("❌ NO Vision Data found (checked Header 3 and Content).")

if __name__ == "__main__":
    inspect_page(16)
    print("\n" + "="*50 + "\n")
    inspect_page(41)
