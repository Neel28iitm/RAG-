
import logging
import os
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from qdrant_client import QdrantClient, models
from src.app.embedding import EmbeddingService
from src.core.vector_store import get_qdrant_client
from flashrank import Ranker, RerankRequest

logger = logging.getLogger('app_logger')

class RetrievalService:
    def __init__(self, config, force_recreate=False):
        self.config = config
        self.force_recreate = force_recreate
        
        # 1. Initialize Dense Embeddings (Google/Gemini) - For Meaning
        self.embedding_service = EmbeddingService(config)
        self.dense_embeddings = self.embedding_service.get_embedding_function()
        
        # 2. Initialize Sparse Embeddings (BM25/SPLADE) - For Keywords
        # Production Tip: FastEmbed runs locally on CPU, very fast for sparse vectors
        # Using "Qdrant/bm25" as it is standard and effective
        self.sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

        # Qdrant Config
        self.collection_name = config['paths']['vector_store_config']['collection_name']
        
        self._initialize_vector_store()
        
        # Initialize Re-ranker (FlashRank)
        self.ranker = Ranker()

    def _initialize_vector_store(self):
        """Initializes Qdrant with Hybrid capabilities"""
        logger.info(f"💾 Initializing Hybrid Qdrant Collection: {self.collection_name}")
        
        try:
             # Use Core Database Module to get client
            self.client = get_qdrant_client(self.config)

            # LangChain Qdrant Wrapper with Hybrid Mode
            self.vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self.dense_embeddings,      # Dense Vector
                sparse_embedding=self.sparse_embeddings, # Sparse Vector (Magic happens here)
                retrieval_mode="hybrid",              # Enable Hybrid Search
            )
            logger.info("✅ Hybrid Vector Store Initialized.")
        except Exception as e:
            msg = f"⚠️ Vector Store init failed (Collection might be missing): {e}"
            logger.warning(msg)
            print(msg) # ERROR VISIBILITY
            self.vector_store = None

    def add_documents(self, documents):
        """Adds documents with both Dense and Sparse vectors"""
        if not documents:
            return
        
        try:
            logger.info(f"📤 Indexing {len(documents)} chunks into Qdrant (Hybrid)...")
            
            if self.vector_store is None:
                # Lazy Create: Collection missing, create it using from_documents
                logger.info("🆕 Creating NEW Qdrant Collection via from_documents...")
                self.vector_store = QdrantVectorStore.from_documents(
                    documents=documents,
                    embedding=self.dense_embeddings,
                    sparse_embedding=self.sparse_embeddings,
                    client=self.client,
                    collection_name=self.collection_name,
                    retrieval_mode="hybrid"
                )
            else:
                self.vector_store.add_documents(documents)
                
            logger.info("✅ Indexing Complete.")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")

    def get_relevant_docs(self, query, top_k=10):
        """Hybrid Retrieval + Reranking Pipeline"""
        try:
            # Step 1: Hybrid Search (Keyword + Semantic)
            # Hum zyada documents fetch karenge (top_k * 3) taaki Reranker ke paas options hon
            # Note: Langchain Qdrant supports 'mmr', 'similarity', but for hybrid, we set mode in constructor
            # similarity_search will use the mode set in constructor (hybrid)
            fetch_k = top_k * 3
            initial_docs = self.vector_store.similarity_search(query, k=fetch_k)
            
            logger.info(f"🔍 Initial Hybrid Search found {len(initial_docs)} docs.")

            if not initial_docs:
                return []

            # Step 2: Reranking (Refining the results)
            logger.info(f"🔄 Reranking {len(initial_docs)} documents...")
            
            passages = [
                {"id": str(idx), "text": doc.page_content, "meta": doc.metadata}
                for idx, doc in enumerate(initial_docs)
            ]
            
            rerank_request = RerankRequest(query=query, passages=passages)
            ranked_results = self.ranker.rerank(rerank_request)
            
            # Top K filter & Reconstruct
            final_docs = []
            for result in ranked_results[:top_k]:
                doc_id = int(result['id']) # ID was stored as str index
                # We need to map back to original docs. list index usage is safe if we use enumerate index as ID
                original_doc = initial_docs[doc_id]
                final_docs.append(original_doc)
                
            return final_docs
        
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
            return []
            
    def clear(self):
        """Clears the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Cleared collection {self.collection_name}")
            # Re-init happens when needed or explicitly called
            # But since QdrantVectorStore holds client references, we might need to re-instantiate it if we want to be safe
            # For now, deleting is enough, subsequent add_documents handles creation if checked (which logic is in core/vector_store)
            # Actually, core/vector_store create checks existence.
            pass
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
