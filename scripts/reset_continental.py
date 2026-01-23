
import os
import sys
from datetime import datetime

sys.path.append(os.getcwd())
from src.core.config import load_config, load_env_robust
from src.core.database import get_db
from src.core.models import FileTracking

load_env_robust()

def reset_file():
    print("🔄 Resetting Continental Bar status...")
    db = next(get_db())
    filename = "25045_Continental_Bar_Nytorgsgatan_33_Stockholm - Uppmätning_musikbuller.pdf"
    
    try:
        record = db.query(FileTracking).filter(FileTracking.filename == filename).first()
        if record:
            print(f"Found record: {record.filename} - {record.status}")
            db.delete(record)
            db.commit()
            print("✅ Record deleted. Trigger script will see it as new.")
        else:
            print("⚠️ Record not found in DB.")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_file()
