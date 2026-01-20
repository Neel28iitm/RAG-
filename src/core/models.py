from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
from src.core.database import Base

class FileTracking(Base):
    __tablename__ = "file_tracking"

    filename = Column(String, primary_key=True, index=True)
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_msg = Column(Text, nullable=True)
