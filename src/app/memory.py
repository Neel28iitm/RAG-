import os
import logging
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger('app_logger')

class MemoryService:
    def __init__(self, redis_url=None):
        # Default to local docker redis if not specified
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def get_history(self, session_id: str):
        """Returns the RedisChatMessageHistory object (List of Messages)"""
        try:
            history = RedisChatMessageHistory(
                session_id=session_id, 
                url=self.redis_url,
                ttl=3600 # 1 Hour TTL
            )
            return history.messages
        except Exception as e:
            logger.error(f"Failed to fetch history for {session_id}: {e}")
            return []

    def add_user_message(self, session_id: str, message: str):
        try:
            history = RedisChatMessageHistory(session_id=session_id, url=self.redis_url, ttl=3600)
            history.add_user_message(message)
        except Exception as e:
            logger.error(f"Failed to add user message: {e}")

    def add_ai_message(self, session_id: str, message: str):
        try:
            history = RedisChatMessageHistory(session_id=session_id, url=self.redis_url, ttl=3600)
            history.add_ai_message(message)
        except Exception as e:
            logger.error(f"Failed to add AI message: {e}")
