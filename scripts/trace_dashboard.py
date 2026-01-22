"""
🕵️ INTEGRITY TRACE DASHBOARD
Checks end-to-end system health: DB -> S3 -> Qdrant
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import get_db
from src.core.models import FileTracking
from src.core.config import load_config
import boto3
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

# Load env & config
load_dotenv()
config = load_config()

class ReportLogger:
    def __init__(self, filename="trace_report.txt"):
        self.filename = filename
        # Clear file
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("")
            
    def log(self, message=""):
        try:
            print(message)
        except UnicodeEncodeError:
            # Fallback for Windows console that doesn't support emojis
            print(message.encode('ascii', 'ignore').decode('ascii'))
            
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(str(message) + "\n")

logger = ReportLogger()

def check_infrastructure():
    logger.log("\n" + "="*80)
    logger.log("🏥 INFRASTRUCTURE HEALTH CHECK")
    logger.log("="*80)
    
    overall_health = True
    
    # 1. API Keys & Env Vars
    required_vars = [
        "QDRANT_URL", "QDRANT_API_KEY", 
        "S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "GOOGLE_API_KEY"
    ]
    
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.log(f"❌ Missing Environment Variables: {', '.join(missing)}")
        overall_health = False
    else:
        logger.log("✅ Environment Variables: Present")

    # 2. Qdrant Connectivity
    try:
        q_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        q_client.get_collections()
        logger.log("✅ Qdrant Connection: Active")
    except Exception as e:
        logger.log(f"❌ Qdrant Connection Failed: {e}")
        overall_health = False

    # 3. S3 Connectivity
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        s3.list_buckets()
        logger.log("✅ S3 Connection: Active")
    except Exception as e:
        logger.log(f"❌ S3 Connection Failed: {e}")
        overall_health = False
        
    return overall_health

def trace_system():
    # Run Health Check First
    if not check_infrastructure():
        logger.log("\n🔴 CRITICAL INFRASTRUCTURE FAILURE. FIX ENV/CONNECTION BEFORE TRACING.")
        logger.log("Skipping detailed trace...")
        return

    logger.log("\n" + "="*80)
    logger.log("🕵️  SYSTEM INTEGRITY DASHBOARD")
    logger.log("="*80)

    # 1. DATABASE LAYER (Source of Truth)
    logger.log("\n1️⃣  DATABASE TRACKING (Upload & Parsing)")
    logger.log("-" * 50)
    
    db = next(get_db())
    files = db.query(FileTracking).all()
    
    db_file_map = {f.filename: f.status for f in files}
    completed_files = [f.filename for f in files if f.status == "COMPLETED"]
    
    logger.log(f"{'Filename':<40} | {'Status':<12} | {'Updated'}")
    logger.log("-" * 80)
    
    for f in files:
        status_icon = "✅" if f.status == "COMPLETED" else "❌" if f.status == "FAILED" else "⏳"
        logger.log(f"{status_icon} {f.filename:<37} | {f.status:<12} | {f.updated_at.strftime('%Y-%m-%d %H:%M')}")
            
    logger.log("-" * 80)
    logger.log(f"Total Files in DB: {len(files)}")
    logger.log(f"Completed: {len(completed_files)}")

    # 2. QDRANT VECTOR LAYER (Fetch Parent IDs)
    logger.log("\n2️⃣  QDRANT VECTOR CHECK (Fetch Parent IDs)")
    logger.log("-" * 50)
    
    try:
        q_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        # Access nested config correctly
        collection_name = config['paths']['vector_store_config']['collection_name']
        
        # Get Collection Info
        info = q_client.get_collection(collection_name)
        total_vectors = info.points_count
        
        logger.log(f"Collection: {collection_name}")
        logger.log(f"Total Vectors (Child Chunks): {total_vectors}")
        
        # Determine Source Alignment
        # Scroll through vectors to get unique 'doc_id' (Parent ID) and 'source'
        parent_ids_in_vector_store = set()
        sources_in_vector_store = set()
        
        # Sample check (limit to 200 points to keep it fast)
        scroll_result, _ = q_client.scroll(
            collection_name=collection_name,
            limit=200,
            with_payload=True,
            with_vectors=False
        )
        
        for point in scroll_result:
            payload = point.payload or {}
            if 'doc_id' in payload:
                parent_ids_in_vector_store.add(payload['doc_id'])
            if 'metadata' in payload and 'source' in payload['metadata']: # Sometimes nested
                sources_in_vector_store.add(payload['metadata']['source'])
            elif 'source' in payload:
                sources_in_vector_store.add(payload['source'])

        logger.log(f"Sampled Parent IDs found: {len(parent_ids_in_vector_store)}")
        logger.log(f"Active Files in Vectors: {len(sources_in_vector_store)}")
        
        # Check if DB files are in Vector Store
        missing_in_vectors = [f for f in completed_files if f not in sources_in_vector_store]
        
        if len(missing_in_vectors) > 0 and len(scroll_result) < total_vectors:
             logger.log("⚠️  Note: Sampling used. Missing files might exist in full scan.")
        elif missing_in_vectors:
             logger.log(f"🔴 MISSING IN VECTORS: {missing_in_vectors}")

    except Exception as e:
        logger.log(f"❌ Qdrant Check Error: {e}")
        parent_ids_in_vector_store = set()

    # 3. S3 STORAGE LAYER (Verify Parent IDs)
    logger.log("\n3️⃣  S3 STORAGE CHECK (Verify Parent chunks)")
    logger.log("-" * 50)
    
    s3 = boto3.client('s3')
    bucket_name = os.getenv("S3_BUCKET_NAME")
    
    try:
        # Check actual S3 keys
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix="parent_store/")
        s3_keys = set()
        
        if 'Contents' in response:
            logger.log(f"Total Objects in S3 parent_store/: {len(response['Contents'])}")
            for obj in response['Contents']:
                # parent_store/{uuid} or parent_store/{uuid}.json ? 
                # ParentDocumentRetriever defaults to UUID keys
                key = obj['Key'].replace("parent_store/", "")
                # Clean up if needed (e.g. remove .json)
                key = key.replace(".json", "") # Just in case
                s3_keys.add(key)
                
        # Handle paginated S3 results if more than 1000
        if response.get('IsTruncated'):
             paginator = s3.get_paginator('list_objects_v2')
             for page in paginator.paginate(Bucket=bucket_name, Prefix="parent_store/"):
                 for obj in page.get('Contents', []):
                     key = obj['Key'].replace("parent_store/", "").replace(".json", "")
                     s3_keys.add(key)
        
        # Cross-reference: Do Qdrant Parent IDs exist in S3?
        found_count = 0
        missing_count = 0
        
        for pid in parent_ids_in_vector_store:
            # pid is typically UUID
            if pid in s3_keys:
                found_count += 1
            else:
                 missing_count += 1
        
        logger.log(f"Verified Parent Chunks (Qdrant -> S3): {found_count}/{len(parent_ids_in_vector_store)}")
        
        if missing_count == 0 and len(parent_ids_in_vector_store) > 0:
            logger.log("✅ INTEGRITY CONFIRMED: All vector parent references exist in S3!")
        elif len(parent_ids_in_vector_store) == 0:
            logger.log("⚠️  No vector parents found to verify.")
        else:
            logger.log(f"🔴 BROKEN REFERENCES: {missing_count} parent chunks missing in S3!")
            
    except Exception as e:
        logger.log(f"❌ S3 Check Error: {e}")

    logger.log("\n" + "="*80)
    logger.log("🏁 TRACE SUMMARY")
    logger.log("="*80)
    
    if total_vectors > 0 and missing_count == 0:
        logger.log("🟢 SYSTEM HEALTHY")
    else:
        logger.log("🟡 SYSTEM WARNING: Check details above.")

if __name__ == "__main__":
    trace_system()
