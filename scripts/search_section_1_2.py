import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv('config/.env')

client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

print("🔍 Searching for 'Section 1.2' and 'L_Aeq' in Report no 32.pdf...")

# Get all chunks without filter (index issue workaround)
all_chunks = []
offset = None
while True:
    results, offset = client.scroll(
        collection_name='rag_production',
        limit=100,
        offset=offset,
        with_payload=True
    )
    all_chunks.extend(results)
    if offset is None:
        break

# Filter for Report 32
report_chunks = [c for c in all_chunks if c.payload.get('metadata', {}).get('source') == 'Report no 32.pdf']
print(f"📦 Found {len(report_chunks)} chunks for Report no 32.pdf\n")

# Search for keywords
keywords = ['Section 1.2', 'L_Aeq', 'precision', 'standard deviation', 'magnitude', 'noise immission']

for keyword in keywords:
    found = False
    for i, chunk in enumerate(report_chunks):
        content = chunk.payload.get('page_content', '')
        if keyword.lower() in content.lower():
            found = True
            print(f"✅ Found '{keyword}' in chunk {i+1}")
            print(f"   Preview: {content[:200]}...\n")
            break
    
    if not found:
        print(f"❌ '{keyword}' NOT found in any chunk\n")

print("\n" + "="*60)
print("Sample of first chunk:")
if report_chunks:
    print(report_chunks[0].payload.get('page_content', '')[:500])
