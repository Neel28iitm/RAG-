import os
import sys
from pathlib import Path

# FORCE LOAD ENV VARS MANUALLY before any other imports
# This bypasses potential load_dotenv issues or import order conflicts
env_path = Path('config/.env')
if env_path.exists():
    print(f"✅ Loading environment from {env_path}")
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
                # Specific check for key
                if key == "GOOGLE_API_KEY":
                    print(f"🔑 GOOGLE_API_KEY set (length: {len(value)})")

sys.path.append(os.getcwd())

import asyncio
# from dotenv import load_dotenv # Skipped, manual load above


from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from src.core.database import get_db
from src.core.models import FileTracking

async def main():
    filename = "Report no 32.pdf"
    file_key = f"raw/{filename}"
    
    print("=" * 60)
    print("🚀 Re-ingesting Report no 32.pdf WITH Auto-Rotation Fix")
    print("=" * 60)
    
    # Check rotation fix status
    rotation_enabled = os.getenv('ENABLE_ROTATION_FIX', 'true').lower() == 'true'
    print(f"\n🔄 Rotation Fix: {'✅ ENABLED' if rotation_enabled else '❌ DISABLED'}")
    
    if not rotation_enabled:
        print("⚠️ WARNING: Rotation fix disabled! Set ENABLE_ROTATION_FIX=true in .env")
    
    config = load_config()
    retriever = RetrievalService(config)
    
    # Step 1: Delete old chunks
    print(f"\n🗑️ Step 1: Deleting old chunks...")
    retriever.delete_documents_by_source(filename)
    print("✅ Old chunks deleted")
    
    # Step 2: Delete DB record
    print(f"\n🗑️ Step 2: Clearing DB record...")
    db = next(get_db())
    record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
    if record:
        db.delete(record)
        db.commit()
        print("✅ DB record cleared")
    db.close()
    
    # Step 3: Ingest with rotation fix
    print(f"\n📥 Step 3: Ingesting with rotation detection...")
    print("⏳ This may take 2-3 minutes...\n")
    
    ingester = DocumentIngestion(config)
    chunks = await ingester.process_file(file_key, check_processed=False)
    
    print(f"\n✅ Generated {len(chunks)} chunks")
    
    # Step 4: Index to Qdrant
    print(f"\n📥 Step 4: Indexing to Qdrant...")
    retriever.add_documents(chunks)
    print("✅ Indexed successfully")
    
    # Step 5: Verify Section 1.2
    print(f"\n🔍 Step 5: Verifying Section 1.2 extraction...")
    
    from qdrant_client import QdrantClient
    client = QdrantClient(
        url=os.getenv('QDRANT_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    # Get all chunks
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
    report_chunks = [c for c in all_chunks if c.payload.get('metadata', {}).get('source') == filename]
    print(f"📦 Total chunks for {filename}: {len(report_chunks)}")
    
    # Search for Section 1.2 keywords
    keywords = ['Section 1.2', 'section 1.2', 'L_Aeq', 'LAeq', 'precision', 'standard deviation']
    
    found_keywords = {}
    for keyword in keywords:
        for chunk in report_chunks:
            content = chunk.payload.get('page_content', '')
            if keyword.lower() in content.lower():
                found_keywords[keyword] = content[:300]
                break
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if found_keywords:
        print(f"✅ SUCCESS! Found {len(found_keywords)}/{len(keywords)} keywords:")
        for kw, preview in found_keywords.items():
            print(f"\n✅ '{kw}':")
            print(f"   {preview}...")
    else:
        print("❌ FAILED: Section 1.2 still not found")
        print("\nSample content from first chunk:")
        if report_chunks:
            print(report_chunks[0].payload.get('page_content', '')[:400])

if __name__ == "__main__":
    asyncio.run(main())
