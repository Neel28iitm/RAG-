"""
Module: Embedding
Purpose: Convert text chunks into vector embeddings using Google Generative AI.
"""

import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings

logger = logging.getLogger('app_logger')

class EmbeddingService:
    def __init__(self, config):
        self.config = config
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            logger.info(f"Initializing Embedding Model: {self.config['embedding']['model_name']}")
            self.model = GoogleGenerativeAIEmbeddings(
                model=self.config['embedding']['model_name'],
                task_type="retrieval_document"
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise e
    
    def get_embedding_function(self) -> Embeddings:
        """Returns the langchain embedding object"""
        return self.model
