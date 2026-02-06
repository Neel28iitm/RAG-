"""
Module: Embedding
Purpose: Convert text chunks into vector embeddings using Google Generative AI.
"""

import logging
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPICallError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger('app_logger')

class RetryEmbeddingWrapper(Embeddings):
    def __init__(self, model, retry_decorator):
        self.model = model
        self.retry_decorator = retry_decorator

    def embed_documents(self, texts):
        return self.retry_decorator(self.model.embed_documents)(texts)

    def embed_query(self, text):
        return self.retry_decorator(self.model.embed_query)(text)


class EmbeddingService:
    def __init__(self, config):
        self.config = config
        self._initialize_model()
    
    def _initialize_model(self):
        try:
            logger.info(f"Initializing Embedding Model: {self.config['embedding']['model_name']}")
            base_model = GoogleGenerativeAIEmbeddings(
                model=self.config['embedding']['model_name'],
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                output_dimensionality=768  # Required for gemini-embedding-001 to match Qdrant config
            )
            
            # --- Apply Exponential Backoff ---
            retry_decorator = retry(
                stop=stop_after_attempt(10), 
                wait=wait_exponential(multiplier=1, min=2, max=60),
                retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, GoogleAPICallError)),
                before_sleep=before_sleep_log(logger, logging.WARNING)
            )
            
            self.model = RetryEmbeddingWrapper(base_model, retry_decorator)
            
            logger.info("✅ Exponential Backoff (Retry) added to Embedding Service via Wrapper.")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise e
    
    def get_embedding_function(self) -> Embeddings:
        """Returns the langchain embedding object"""
        return self.model
