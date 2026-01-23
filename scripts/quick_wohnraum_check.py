import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv('config/.env')

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

print("🔍 Searching for 'Wohnraum' in Report no 32.pdf...")

results = client.scroll(
    collection_name='rag_production',
    scroll_filter={
        'must': [
            {'key': 'metadata.source', 'match': {'value': 'Report no 32.pdf'}}
        ]
    },
    limit=200,
    with_payload=True
)[0]

print(f"📦 Found {len(results)} chunks for Report no 32.pdf")

found = False
for i, hit in enumerate(results):
    content = hit.payload.get('page_content', '')
    if 'Wohnraum' in content:
        found = True
        print(f"\n✅ FOUND 'Wohnraum' in chunk {i+1}!")
        print("-" * 50)
        print(content[:500])
        print("-" * 50)
        break

if not found:
    print("\n❌ 'Wohnraum' NOT FOUND in any chunk.")
    print("\nSample content from chunk 1:")
    if results:
        print(results[0].payload.get('page_content', '')[:500])
