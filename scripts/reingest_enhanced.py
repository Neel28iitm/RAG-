import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv('config/.env')

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService

async def main():
    filename = "Report no 32.pdf"
    file_key = f"raw/{filename}"
    
    print(f"🚀 Re-ingesting {filename} with CLEAN vendor multimodal...")
    print("✅ Model: gemini-2.5-flash")
    print("✅ Rotation Handling: Enabled (via system_prompt)")
    print("❌ Premium Mode: DISABLED (conflict removed)\n")
    
    config = load_config()
    
    print(f"📥 Step 1: Processing with enhanced LlamaParse...")
    ingester = DocumentIngestion(config)
    chunks = await ingester.process_file(file_key, check_processed=False)
    
    print(f"\n✅ Generated {len(chunks)} chunks")
    
    print(f"\n📥 Step 2: Indexing to Qdrant...")
    retriever = RetrievalService(config)
    retriever.add_documents(chunks)
    
    print("\n🎯 DONE! Now checking for 'Wohnraum'...\n")
    
    # Quick verification
    from qdrant_client import QdrantClient
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    # Scroll without filter (index issue)
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
    
    # Filter in Python
    report_chunks = [c for c in all_chunks if c.payload.get('metadata', {}).get('source') == filename]
    print(f"📦 Found {len(report_chunks)} chunks for {filename}")
    
    found = False
    for i, hit in enumerate(report_chunks):
        content = hit.payload.get('page_content', '')
        if 'Wohnraum' in content:
            found = True
            print(f"\n✅ SUCCESS! Found 'Wohnraum' in chunk {i+1}!")
            print("-" * 60)
            print(content[:600])
            print("-" * 60)
            break
    
    if not found:
        print("\n❌ 'Wohnraum' still not found.")
        print("Sample content from first chunk:")
        if report_chunks:
            print(report_chunks[0].payload.get('page_content', '')[:400])

if __name__ == "__main__":
    asyncio.run(main())
