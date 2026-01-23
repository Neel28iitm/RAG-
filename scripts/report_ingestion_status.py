import sys
import os

# Force UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import get_db
from src.core.models import FileTracking
from sqlalchemy import func

def main():
    print("📊 Generating Ingestion Status Report...\n")
    
    db = next(get_db())
    try:
        # Get Counts
        results = db.query(FileTracking.status, func.count(FileTracking.status)).group_by(FileTracking.status).all()
        
        counts = {status: count for status, count in results}
        total = sum(counts.values())
        
        print(f"Total Documents Tracked: {total}")
        print("-" * 30)
        
        for status, count in counts.items():
            icon = "✅" if status == "COMPLETED" else "❌" if status == "FAILED" else "⏳"
            print(f"{icon} {status}: {count}")
            
        print("-" * 30)
        
        # List Failed/Pending details
        incomplete = db.query(FileTracking).filter(FileTracking.status != "COMPLETED").all()
        if incomplete:
            print("\n⚠️  Incomplete/Failed Files:")
            for f in incomplete:
                print(f" - {f.filename} [{f.status}]")
                if f.error_msg:
                    print(f"   Reason: {f.error_msg[:100]}...")
        else:
            print("\n✨ All documents processed successfully!")

    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
