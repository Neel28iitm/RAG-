
import os
import sys
import json
import boto3
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load envs
load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("🔍 Deep Inspecting Qdrant Point Payload...")
    
    url = os.getenv("QDRANT_URL")
    key = os.getenv("QDRANT_API_KEY")
    
    if not url:
        print("❌ QDRANT_URL not found!")
        return

    print(f"🌐 Connecting to: {url}")
    client = QdrantClient(url=url, api_key=key)
    
    collection_name = "rag_production"
    
    # Scroll 1 point
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_payload=True,
        with_vectors=False
    )
    
    if not points:
        print("❌ Collection is EMPTY!")
        return

    point = points[0]
    payload = point.payload
    
    print("\n📦 Payload Dump:")
    print(json.dumps(payload, indent=2, default=str))
    
    # Check linkage
    # Expected key: 'doc_id' or 'parent_id' or something similar used by ParentDocumentRetriever
    # LangChain default is 'doc_id' usually.
    
    doc_id = payload.get('doc_id')
    
    if not doc_id:
        print("\n⚠️ No 'doc_id' found in payload! Searching for other ID keys...")
        # Check explicit keys
        for k,v in payload.items():
            if 'id' in k:
                print(f" - Candidate Key: {k} = {v}")
                doc_id = v # Try last one?
    
    if doc_id:
        print(f"\n🔗 Checking S3 for ID: {doc_id}")
        bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
        prefix = "parent_store/"
        full_key = prefix + str(doc_id)
        
        s3 = boto3.client('s3', 
                         aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                         aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                         region_name=os.getenv("AWS_REGION", "ap-south-1"))
        
        try:
            s3.head_object(Bucket=bucket_name, Key=full_key)
            print(f"✅ S3 Object Found! Linkage is GOOD.")
        except Exception as e:
            print(f"❌ S3 Object NOT FOUND (Key: {full_key}). Linkage is BROKEN.")
            print(f"Error: {e}")
            
    else:
        print("❌ Could not determine Parent ID from payload.")

if __name__ == "__main__":
    main()
