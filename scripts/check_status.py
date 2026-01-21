"""
Quick script to check document ingestion status
"""
from src.core.database import get_db
from src.core.models import FileTracking

def check_status():
    db = next(get_db())
    
    print("="*60)
    print("📊 DOCUMENT INGESTION STATUS")
    print("="*60)
    
    files = db.query(FileTracking).order_by(FileTracking.updated_at.desc()).all()
    
    # Summary
    total = len(files)
    completed = sum(1 for f in files if f.status == 'COMPLETED')
    failed = sum(1 for f in files if f.status == 'FAILED')
    processing = sum(1 for f in files if 'RETRY' in f.status or f.status == 'PROCESSING')
    
    print(f"\n📈 Summary:")
    print(f"   Total: {total}")
    print(f"   ✅ Completed: {completed}")
    print(f"   ⏳ Processing/Retry: {processing}")
    print(f"   ❌ Failed: {failed}")
    
    # Details
    print(f"\n📋 Details:\n")
    for f in files:
        status_icon = {
            'COMPLETED': '✅',
            'FAILED': '❌',
            'PROCESSING': '⏳',
            'RETRY_1': '🔄',
            'RETRY_2': '🔄',
            'RETRY_3': '🔄'
        }.get(f.status, '❓')
        
        print(f"{status_icon} {f.filename:<40} {f.status:<15} {f.updated_at}")
        if f.error_msg:
            print(f"   Error: {f.error_msg[:100]}")
    
    db.close()

if __name__ == "__main__":
    check_status()
