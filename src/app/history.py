from datetime import datetime
from sqlalchemy.orm import Session
from src.core.database import get_db, init_db, ChatSession

class ChatHistoryManager:
    def __init__(self):
        # Ensure tables exist
        init_db()

    def _get_db_session(self):
        """Helper to get a fresh DB session"""
        return next(get_db())

    def create_session(self):
        """Creates a new session and returns its ID."""
        db = self._get_db_session()
        try:
            new_session = ChatSession(title="New Chat")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            return new_session.id
        finally:
            db.close()

    def get_session(self, session_id):
        """Returns session dict or None"""
        db = self._get_db_session()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                return {
                    "id": session.id,
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "messages": session.messages if session.messages else []
                }
            return None
        finally:
            db.close()
    
    def get_all_sessions(self):
        """Returns sessions sorted by date (newest first)."""
        db = self._get_db_session()
        try:
            sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
            # Return list of tuples (id, data_dict) to match previous interface
            result = []
            for s in sessions:
                data = {
                    "title": s.title,
                    "created_at": s.created_at.isoformat(),
                    # We don't necessarily need all messages for the list view, but keeping it consistent
                    "messages": s.messages
                }
                result.append((s.id, data))
            return result
        finally:
            db.close()

    def add_message(self, session_id, role, content):
        db = self._get_db_session()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                return
            
            new_msg = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # JSON mutation in SQLAlchemy usually needs reassignment to trigger tracking
            # Create a copy of the list, append, and reassign
            current_msgs = list(session.messages) if session.messages else []
            current_msgs.append(new_msg)
            session.messages = current_msgs
            
            # Auto-update title if it's the first user message
            if len(current_msgs) <= 2: 
                 if role == "user":
                     title = content[:30] + "..." if len(content) > 30 else content
                     session.title = title
            
            db.commit()
        except Exception as e:
            print(f"Error adding message: {e}")
            db.rollback()
        finally:
            db.close()

    def delete_session(self, session_id):
        db = self._get_db_session()
        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
        finally:
            db.close()
