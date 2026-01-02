"""
Module: Database
Purpose: Qdrant Database Connectivity
"""
import os
import logging
from qdrant_client import QdrantClient, models

logger = logging.getLogger('app_logger')

def get_qdrant_client(config):
    """Initializes and returns a QdrantClient"""
    url = config['paths']['vector_store_config']['url']
    collection_name = config['paths']['vector_store_config']['collection_name']
    
    logger.info(f"💾 Connecting to Qdrant at {url}")
    
    try:
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key, prefer_grpc=False)
        
        # Test connection
        client.get_collections()
        
        # We removed auto-creation here to allow Hybrid/Sparse collections to be managed by RetrievalService
            
        return client
            
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        raise e
