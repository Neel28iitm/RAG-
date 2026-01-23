
import os
import sys
import boto3
from qdrant_client import QdrantClient

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import load_env_robust
load_env_robust("config/.env")
load_env_robust(".env")

from src.core.database import get_db, init_db
from src.core.models import FileTracking
from src.core.config import load_config

def reset_system():
    print("⚠️  WARNING: This will DELETE ALL DATA (Qdrant Vectors + S3 Parent Docs + Local Status).")
    print("Source PDFs in 'raw/' folder will NOT be touched.\n")
    
    # helper for confirmation
    # confirm = input("Type 'yes' to proceed: ")
    # if confirm.lower() != 'yes':
    #     print("Aborted.")
    #     return

    config = load_config("config/settings.yaml")
    
    # 1. Clear Qdrant
    print("Step 1: Clearing Qdrant Collection...")
    try:
        q_url = os.getenv("QDRANT_URL")
        q_key = os.getenv("QDRANT_API_KEY")
        collection_name = config['paths']['vector_store_config']['collection_name']
        
        client = QdrantClient(url=q_url, api_key=q_key)
        client.delete_collection(collection_name)
        print(f"✅ Deleted Collection: {collection_name}")
    except Exception as e:
        print(f"❌ Qdrant Error (ignoring): {e}")

    # 2. Clear S3 Parent Store
    print("Step 2: Clearing S3 Parent Store (parent_store/)...")
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        bucket_name = os.getenv("S3_BUCKET_NAME")
        prefix = "parent_store/"
        
        # List and Delete
        objects_to_delete = []
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            print(f"Found {len(objects_to_delete)} objects to delete...")
            # Batch Delete (1000 max)
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i+1000]
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': batch})
                print(f"   Deleted batch {i}-{i+len(batch)}")
            print("✅ S3 Parent Store Cleared.")
        else:
            print("✅ S3 Parent Store was already empty.")
            
    except Exception as e:
        print(f"❌ S3 Error: {e}")

    # 3. Clear Local DB
    print("Step 3: Resetting Local Database...")
    try:
        db = next(get_db())
        count = db.query(FileTracking).delete()
        db.commit()
        db.close()
        print(f"✅ Deleted {count} records from FileTracking.")
    except Exception as e:
        print(f"❌ DB Error: {e}")

    print("\n✨ SYSTEM FULLY RESET. READY FOR FRESH INGESTION.")

if __name__ == "__main__":
    reset_system()
