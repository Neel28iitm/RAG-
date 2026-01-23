
import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path

# Load env
env_path = Path('config/.env')
if not env_path.exists():
    env_path = Path('.env')
load_dotenv(env_path)

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

print("🔧 Ensuring index on 'metadata.source'...")
try:
    client.create_payload_index(
        collection_name='rag_production',
        field_name='metadata.source',
        field_schema='keyword'
    )
    print("✅ Index created/exists.")
except Exception as e:
    print(f"⚠️ Index creation warning: {e}")

print("🔍 Inspecting 'Report no 32.pdf' content...")

try:
    results = client.scroll(
        collection_name='rag_production',
        scroll_filter={
            'must': [
                {'key': 'metadata.source', 'match': {'value': 'Report no 32.pdf'}}
            ]
        },
        limit=5,
        with_payload=True
    )[0]

    print(f"✅ Found {len(results)} sample chunks.\n")

    for i, hit in enumerate(results):
        content = hit.payload.get('page_content', hit.payload.get('text', ''))
        print(f"--- CHUNK {i+1} START ---")
        print(content[:600] + "..." if len(content) > 600 else content)
        print("--- CHUNK END ---\n")

except Exception as e:
    print(f"❌ Error: {e}")
