import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.core.database import get_db, init_db
from src.core.models import FileTracking
from src.core.config import load_config
from src.core.vector_store import get_qdrant_client

def verify_status():
    print("🔍 Starting Verification Process...\n")
    
    # 1. Check SQLite (File Status)
    print("--- 1. Checking Database (File Tracking) ---")
    try:
        db = next(get_db())
        files = db.query(FileTracking).all()
        
        if not files:
            print("⚠️ No files found in tracking database.")
        else:
            print(f"✅ Found {len(files)} files in database:")
            for f in files:
                status_icon = "✅" if f.status == "COMPLETED" else "❌" if f.status == "FAILED" else "⏳"
                print(f"   {status_icon} {f.filename}: {f.status}")
                if f.error_msg:
                    print(f"      🔴 Error: {f.error_msg}")
    except Exception as e:
        print(f"❌ Database Error: {e}")

    print("\n")

    # 2. Check Qdrant (Vector Count)
    print("--- 2. Checking Qdrant (Vector Store) ---")
    try:
        config = load_config()
        client = get_qdrant_client(config)
        collection_name = config['paths']['vector_store_config']['collection_name']
        
        try:
            info = client.get_collection(collection_name)
            points_count = info.points_count
            print(f"✅ Collection '{collection_name}' exists.")
            print(f"📊 Total Vectors Stored: {points_count}")
            
            if points_count == 0:
                print("⚠️ Collection is empty. Ingestion might have failed or is in progress.")
            else:
                print("✅ Data is present in Vector DB.")
                
        except Exception as e:
            print(f"❌ Collection '{collection_name}' not found or error accessing Qdrant: {e}")

    except Exception as e:
        print(f"❌ Qdrant Connection Error: {e}")

if __name__ == "__main__":
    verify_status()
