from src.core.database import get_db
from src.core.models import FileTracking

def delete_record():
    db = next(get_db())
    record = db.query(FileTracking).filter(FileTracking.filename == 'Report no 32.pdf').first()
    if record:
        db.delete(record)
        db.commit()
        print('✅ Deleted record')
    else:
        print('ℹ️ No record found')
    db.close()

if __name__ == "__main__":
    delete_record()
