
import sys
import os
import asyncio

# Fix Path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.core.config import load_config, load_env_robust
from src.core.vector_store import get_qdrant_client

load_env_robust()
config = load_config("config/settings.yaml")

def inspect_content():
    client = get_qdrant_client(config)
    collection_name = config['paths']['vector_store_config']['collection_name']
    filename = "SS_25268_2023 Byggnadsakustik.pdf"
    
    print(f"🔎 Inspecting content for: {filename}")
    
    # 1. Search for '48 dB'
    print("\n--- Searching for '48 dB' ---")
    points, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter={
            "must": [
                {"key": "metadata.source", "match": {"text": filename}},
            ]
        },
        limit=1000,
        with_payload=True
    )
    
    matches = 0
    for pt in points:
        text = pt.payload.get('page_content', '')
        # Check for keywords related to the user's query
        if "48" in text:
            print(f"\n[Chunk {pt.id}] Page {pt.payload.get('metadata', {}).get('page_label', '?')}")
            print(f"--- FULL CONTENT START ---\n{text}\n--- FULL CONTENT END ---")
            matches += 1
            if matches > 3: break # Show first 3 matches
            
    if matches == 0:
        print("❌ Critical keywords (48 dB, consultation/samtalsrum) NOT FOUND in any chunk.")
    else:
        print(f"\n✅ Found {matches} relevant chunks.")

if __name__ == "__main__":
    inspect_content()
