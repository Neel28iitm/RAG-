"""
Module: Database
Purpose: SQLAlchemy Database Setup for Chat History (SQLite/Postgres)
"""
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import os

# Production mein hum isse Postgres URL se replace kar denge
DATABASE_URL = "sqlite:///./rag_app.db"

Base = declarative_base()

# check_same_thread: False is needed for SQLite when used with FastAPI/Streamlit reloading
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Models ---
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Messages ko hum JSON ki tarah store karenge (Simple approach for now)
    messages = Column(JSON, default=list)

# Init DB: Create Tables if not exist
def init_db():
    # Import all models here so they are registered with Base.metadata
    from src.core.models import FileTracking
    Base.metadata.create_all(bind=engine)
