
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path

# Load env
load_dotenv('config/.env')

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

print("🔍 Listing distinct sources in 'rag_production'...")

# Scroll all and collect sources (inefficient but works for 2000 chunks)
sources = set()
offset = None
count = 0

while True:
    results, offset = client.scroll(
        collection_name='rag_production',
        limit=100,
        offset=offset,
        with_payload=True,
        with_vectors=False
    )
    for hit in results:
        meta = hit.payload.get('metadata', {})
        src = meta.get('source', 'Unknown')
        sources.add(src)
    
    count += len(results)
    if offset is None:
        break

print(f"📦 Scanned {count} chunks.")
print("sources found:")
for s in sorted(list(sources)):
    print(f" - {s}")
