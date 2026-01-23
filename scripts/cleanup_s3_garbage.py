
import os
import sys
import logging
from typing import Set

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Robust Env Loading
from src.core.config import load_env_robust
load_env_robust(".env")

import boto3
from qdrant_client import QdrantClient

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_active_doc_ids(client: QdrantClient, collection_name: str) -> Set[str]:
    """Scans Qdrant to find all referenced Parent Document IDs."""
    logger.info("🔍 Scanning Qdrant for active Document IDs...")
    active_ids = set()
    
    # Scroll through all points
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=None,
            limit=100,
            with_payload=True,
            with_vectors=False,
            offset=offset
        )
        
        for point in points:
            # ParentDocumentRetriever stores ID in 'doc_id' field of payload
            if point.payload and 'doc_id' in point.payload:
                active_ids.add(point.payload['doc_id'])
                
        if next_offset is None:
            break
        offset = next_offset
        
    logger.info(f"✅ Found {len(active_ids)} unique active Parent IDs in Qdrant.")
    return active_ids

def cleanup_s3(active_ids: Set[str]):
    """Deletes S3 objects that are missing from the active_ids set."""
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION")
    )
    bucket_name = os.getenv("S3_BUCKET_NAME")
    prefix = "parent_store/" # Must match RetrievalService prefix
    
    logger.info(f"🔍 Scanning S3 Bucket: {bucket_name}/{prefix}")
    
    objects_to_delete = []
    paginator = s3.get_paginator('list_objects_v2')
    
    total_s3_objects = 0
    
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            # Key format in S3 is usually "parent_store/UUID"
            # We need to extract the UUID part to match Qdrant's doc_id
            # LangChain DocStore usually stores exact key matching doc_id? 
            # Or does it append UUID? 
            # Default EncoderBackedStore logic: key = prefix + key_in_docstore (which is doc_id)
            
            # Let's verify: key "parent_store/abc-123" -> doc_id "abc-123"
            if not key.startswith(prefix):
                continue
                
            doc_id_in_s3 = key[len(prefix):] # Strip prefix
            
            if doc_id_in_s3 not in active_ids:
                objects_to_delete.append(key)
            
            total_s3_objects += 1

    logger.info(f"📊 S3 Stats: Total Objects={total_s3_objects}, Active={len(active_ids)}, Garbage={len(objects_to_delete)}")
    
    if not objects_to_delete:
        logger.info("✨ S3 is clean. No garbage found.")
        return

    print(f"\n⚠️  WARNING: Found {len(objects_to_delete)} orphaned objects in S3.")
    print("These objects exist in S3 but are NOT linked to any vector in Qdrant.")
    confirmation = input("Do you want to DELETE them? (Type 'yes' to confirm): ")
    
    if confirmation.lower() == 'yes':
        logger.info("🗑️  Deleting garbage objects...")
        
        # Batch delete (max 1000 per request)
        batch_size = 1000
        for i in range(0, len(objects_to_delete), batch_size):
            batch = objects_to_delete[i:i + batch_size]
            delete_request = {'Objects': [{'Key': k} for k in batch]}
            s3.delete_objects(Bucket=bucket_name, Delete=delete_request)
            logger.info(f"   Deleted batch {i}-{i+len(batch)}")
            
        logger.info("✅ Cleanup Complete.")
    else:
        logger.info("❌ Cleanup aborted.")

def main():
    # Load settings to get Qdrant config
    from src.core.config import load_config
    config = load_config("config/settings.yaml")
    
    q_url = os.getenv("QDRANT_URL")
    q_key = os.getenv("QDRANT_API_KEY")
    collection_name = config['paths']['vector_store_config']['collection_name']
    
    # Init Qdrant
    client = QdrantClient(url=q_url, api_key=q_key)
    
    # 1. Get Valid IDs
    active_ids = get_active_doc_ids(client, collection_name)
    
    if not active_ids:
        print("❌ No active vectors found in Qdrant. Skipping cleanup to avoid accidental wipe.")
        return

    # 2. Cleanup S3
    cleanup_s3(active_ids)

if __name__ == "__main__":
    main()
