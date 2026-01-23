
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

FILENAME = "Report no 32.pdf"

# Search for multiple related keywords
KEYWORDS = ["Wohnraum", "Living Room", "Raum", "dB", "noise", "acoustic", "graph", "chart", "Bild"]

print(f"🔍 Diagnostic Search in '{FILENAME}'")
print("=" * 60)

try:
    results = client.scroll(
        collection_name='rag_production',
        scroll_filter={
            'must': [
                {'key': 'metadata.source', 'match': {'value': FILENAME}}
            ]
        },
        limit=100,
        with_payload=True
    )[0]

    print(f"📦 Total chunks retrieved: {len(results)}\n")

    keyword_stats = {}
    
    for keyword in KEYWORDS:
        matches = []
        for hit in results:
            content = hit.payload.get('page_content', hit.payload.get('text', ''))
            if keyword.lower() in content.lower():
                matches.append({
                    'content': content,
                    'score': getattr(hit, 'score', None)
                })
        
        keyword_stats[keyword] = len(matches)
        
        if matches:
            print(f"✅ '{keyword}': Found in {len(matches)} chunk(s)")
            # Show first match snippet
            snippet = matches[0]['content'][:300]
            print(f"   Sample: {snippet}...\n")
        else:
            print(f"❌ '{keyword}': NOT FOUND\n")

    print("=" * 60)
    print("\n📊 Summary:")
    print(f"Keywords found: {sum(1 for v in keyword_stats.values() if v > 0)}/{len(KEYWORDS)}")
    print(f"Keywords missing: {sum(1 for v in keyword_stats.values() if v == 0)}/{len(KEYWORDS)}")
    
    missing = [k for k, v in keyword_stats.items() if v == 0]
    if missing:
        print(f"\n❌ Missing keywords: {', '.join(missing)}")
    
    print("\n🎯 DIAGNOSIS:")
    if keyword_stats.get("Wohnraum", 0) == 0:
        if keyword_stats.get("Raum", 0) > 0 or keyword_stats.get("dB", 0) > 0:
            print("⚠️  PARTIAL INGESTION: Some acoustic data exists but 'Wohnraum' label missing")
            print("   → Likely a GRAPH PARSING issue (labels not extracted)")
            print("   → Solution: Enable Vision Enhancement for graph-heavy pages")
        else:
            print("❌ COMPLETE INGESTION FAILURE: No acoustic/room data found")
            print("   → The entire graph/table was not extracted")
            print("   → Solution: Vision Enhancement + manual verification")
    else:
        print("✅ DATA EXISTS: This is a RETRIEVAL problem, not ingestion")
        print("   → Solution: Improve query rewriting or reranking")

except Exception as e:
    print(f"❌ Error: {e}")
