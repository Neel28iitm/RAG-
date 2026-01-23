import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import get_db
from src.core.models import FileTracking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_status():
    logger.info("🛠️  Resetting FileTracking status...")
    db = next(get_db())
    try:
        # Option 1: Delete all to force full re-scan
        deleted = db.query(FileTracking).delete()
        db.commit()
        logger.info(f"✅ Deleted {deleted} records. Next ingestion scan will re-queue them.")
        
    except Exception as e:
        logger.error(f"❌ Error resetting DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_status()
