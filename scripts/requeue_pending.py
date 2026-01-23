
import os
import sys

# Add src 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import load_env_robust
load_env_robust(".env")

from src.core.database import get_db
from src.core.models import FileTracking
from src.core.config import load_config
from src.worker.tasks import process_document_task

def requeue_pending():
    db = next(get_db())
    config = load_config("config/settings.yaml")
    
    pending_files = db.query(FileTracking).filter(FileTracking.status.in_(['PENDING', 'FAILED'])).all()
    
    if not pending_files:
        print("✅ No PENDING files found to requeue.")
        return

    print(f"🔄 Found {len(pending_files)} pending files. Re-queuing...")
    
    for file_record in pending_files:
        print(f"   -> Re-queuing: {file_record.filename}")
        # BUG FIX: Use S3 key 'raw/filename', NOT local path
        s3_key = f"raw/{file_record.filename}"
        
        # Send to Celery
        process_document_task.delay(s3_key, config)
        
    print("🚀 Done. Check worker logs.")

if __name__ == "__main__":
    requeue_pending()
