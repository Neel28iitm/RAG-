import logging
import os
import pickle
import boto3
from typing import Iterator, List, Optional, Sequence, Tuple
from langchain_core.stores import ByteStore
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from qdrant_client import QdrantClient, models
from src.app.embedding import EmbeddingService
from src.core.vector_store import get_qdrant_client
import cohere  # Multilingual reranker
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# Parent-Child Dependencies
print("DEBUG: Importing ParentDocumentRetriever...")
try:
    from langchain.retrievers import ParentDocumentRetriever
    print("DEBUG: Success langchain.retrievers")
except ImportError as e:
    print(f"DEBUG: Failed langchain.retrievers: {e}")
    try:
        from langchain_classic.retrievers import ParentDocumentRetriever
        print("DEBUG: Success langchain_classic.retrievers")
    except ImportError as e2:
        print(f"DEBUG: Failed langchain_classic.retrievers: {e2}")
        raise ImportError(f"Could not import ParentDocumentRetriever. Original: {e}, Classic: {e2}")

print("DEBUG: Importing LocalFileStore & EncoderBackedStore...")
try:
    from langchain.storage import LocalFileStore, EncoderBackedStore
    print("DEBUG: Success langchain.storage")
except ImportError:
    try:
        from langchain_classic.storage import LocalFileStore, EncoderBackedStore
        print("DEBUG: Success langchain_classic.storage")
    except ImportError:
        try:
             # Try mixing?
             from langchain.storage.file_system import LocalFileStore
             from langchain.storage.encoder_backed import EncoderBackedStore
             print("DEBUG: Success langchain.storage.*")
        except ImportError:
             raise ImportError("Could not import LocalFileStore/EncoderBackedStore")

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger('app_logger')

class S3Store(ByteStore):
    """Custom ByteStore implementation for AWS S3"""
    def __init__(self, bucket_name: str, prefix: str = "", client=None, redis_url: str = "redis://localhost:6379/0"):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.client = client or boto3.client('s3')
        
        # Redis Cache Initialization
        import redis
        try:
            self.redis = redis.from_url(redis_url)
            self.redis.ping() # Check connection
            self.use_redis = True
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}. Falling back to S3 direct.")
            self.use_redis = False

    def mget(self, keys: Sequence[str]) -> List[Optional[bytes]]:
        results = [None] * len(keys)
        keys_to_fetch_from_s3 = []
        indices_to_fetch = []

        # 1. Check Redis Cache
        if self.use_redis:
            try:
                # Batch get from Redis
                # Prefix keys in Redis to avoid collisions
                redis_keys = [f"parent_doc:{k}" for k in keys]
                cached_values = self.redis.mget(redis_keys)
                
                for i, val in enumerate(cached_values):
                    if val is not None:
                        results[i] = val
                    else:
                        keys_to_fetch_from_s3.append(keys[i])
                        indices_to_fetch.append(i)
            except Exception as e:
                # Redis failure fallback
                print(f"⚠️ Redis read failed: {e}")
                keys_to_fetch_from_s3 = list(keys)
                indices_to_fetch = list(range(len(keys)))
        else:
             keys_to_fetch_from_s3 = list(keys)
             indices_to_fetch = list(range(len(keys)))

        if not keys_to_fetch_from_s3:
            return results

        # 2. Fetch Missing from S3 (Parallel)
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch_s3_and_cache_redis(idx_key_tuple):
            idx, key = idx_key_tuple
            full_key = self.prefix + key
            try:
                response = self.client.get_object(Bucket=self.bucket_name, Key=full_key)
                data = response['Body'].read()
                
                # Cache in Redis (Async/Fire-and-forget ideally, but blocking here needed for now)
                # Set TTL to 24 hours (86400 seconds)
                if self.use_redis:
                    try:
                        self.redis.setex(f"parent_doc:{key}", 86400, data)
                    except Exception:
                        pass 

                return idx, data
            except Exception:
                return idx, None

        with ThreadPoolExecutor(max_workers=10) as executor:  # Optimized: reduced from 50 to 10
            fetched_results = list(executor.map(fetch_s3_and_cache_redis, zip(indices_to_fetch, keys_to_fetch_from_s3)))
            
        # 3. Merge Results
        for idx, data in fetched_results:
            results[idx] = data
            
        return results

    def mset(self, key_value_pairs: Sequence[Tuple[str, bytes]]) -> None:
        # 1. Write to S3 (Primary)
        for key, value in key_value_pairs:
            full_key = self.prefix + key
            self.client.put_object(Bucket=self.bucket_name, Key=full_key, Body=value)
            
            # 2. Update Redis
            if self.use_redis:
                try:
                    self.redis.setex(f"parent_doc:{key}", 86400, value)
                except Exception as e:
                    print(f"⚠️ Redis write failed: {e}")

    def mdelete(self, keys: Sequence[str]) -> None:
        for key in keys:
            # 1. Delete S3
            full_key = self.prefix + key
            self.client.delete_object(Bucket=self.bucket_name, Key=full_key)
            
            # 2. Delete Redis
            if self.use_redis:
                try:
                    self.redis.delete(f"parent_doc:{key}")
                except Exception:
                    pass

    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        # Minimal implementation for listing if needed
        full_prefix = self.prefix + (prefix or "")
        paginator = self.client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=full_prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.startswith(self.prefix):
                    yield key[len(self.prefix):]


class RetrievalService:
    def __init__(self, config, force_recreate=False):
        self.config = config
        self.force_recreate = force_recreate
        
        # 1. Initialize Dense Embeddings
        self.embedding_service = EmbeddingService(config)
        self.dense_embeddings = self.embedding_service.get_embedding_function()
        
        # 2. Initialize Sparse Embeddings
        self.sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

        # Qdrant Config
        self.collection_name = config['paths']['vector_store_config']['collection_name']
        
        # 3. Initialize Parent-Child Components
        self._initialize_components()
        
        # Initialize Cohere Reranker (Multilingual)
        try:
            self.cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
            logger.info("✅ Cohere Multilingual Reranker initialized")
        except Exception as e:
            logger.error(f"❌ Cohere initialization failed: {e}")
            self.cohere_client = None
        
        # Initialize Query Rewriter LLM (Gemini 2.5 Flash)
        self.rewriter_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1, # Low temp for precision
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    def _initialize_components(self):
        """Initializes Qdrant, DocStore, and ParentDocumentRetriever"""
        logger.info(f"💾 Initializing Hybrid Qdrant + Parent Retriever: {self.collection_name}")
        
        try:
            self.client = get_qdrant_client(self.config)

            # A. Child Vector Store (Qdrant)
            try:
                exists = self.client.collection_exists(self.collection_name)
            except Exception:
                exists = False
            
            if not exists:
                logger.info(f"🆕 Collection {self.collection_name} missing. Creating manually...")
                try:
                    self.client.recreate_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
                        sparse_vectors_config={
                            "text-sparse": models.SparseVectorParams(
                                index=models.SparseIndexParams(on_disk=False)
                            )
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to create collection: {e}")

            # Ensure Payload Indexes Exist (Critical for Filtering)
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="metadata.source",
                    field_schema=models.PayloadSchemaType.TEXT
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="metadata.page_label",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
            except Exception:
                pass # Indices might already exist

            # Initialize Store
            try:
                self.vector_store = QdrantVectorStore(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding=self.dense_embeddings,      
                    sparse_embedding=self.sparse_embeddings,
                    retrieval_mode="hybrid",
                    sparse_vector_name="text-sparse"
                )
            except Exception as e_init:
                print(f"DEBUG: QdrantVectorStore init failed ({e_init}). Forcing Re-Creation.")
                self.client.recreate_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
                        sparse_vectors_config={
                            "text-sparse": models.SparseVectorParams(
                                index=models.SparseIndexParams(on_disk=False)
                            )
                        }
                )
                self.vector_store = QdrantVectorStore(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding=self.dense_embeddings,      
                    sparse_embedding=self.sparse_embeddings,
                    retrieval_mode="hybrid",
                    sparse_vector_name="text-sparse"
                )
            
            # B. Parent Document Store (S3 Backed)
            bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
            prefix = "parent_store/"
            
            try:
                from botocore.config import Config
                
                s3_config = Config(
                    max_pool_connections=50,
                    retries={'max_attempts': 3}
                )

                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    region_name=os.getenv("AWS_REGION", "us-east-1"),
                    config=s3_config
                )
                
                self.s3_store = S3Store(client=s3_client, bucket_name=bucket_name, prefix=prefix)
                logger.info(f"☁️  Connected to S3 DocStore: {bucket_name}/{prefix}")
            except Exception as e_s3:
                logger.error(f"❌ Failed to connect to S3: {e_s3}")
                raise e_s3
            
            # Correct Argument Names for this version of LangChain
            def pickle_encoder(obj):
                return pickle.dumps(obj)
            def pickle_decoder(data):
                return pickle.loads(data) if data else None

            self.docstore = EncoderBackedStore(
                store=self.s3_store,
                key_encoder=lambda x: x,
                value_serializer=pickle_encoder,
                value_deserializer=pickle_decoder
            )
            
            # C. Child Splitter
            child_size = self.config['parsing'].get('child_chunk_size', 400)
            child_overlap = self.config['parsing'].get('child_chunk_overlap', 50) # [NEW]
            self.child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=child_size,
                chunk_overlap=child_overlap
            )
            
            # D. Parent Document Retriever
            self.retriever = ParentDocumentRetriever(
                vectorstore=self.vector_store,
                docstore=self.docstore,
                child_splitter=self.child_splitter,
                parent_splitter=None, # Incoming docs are already "Parents"
            )
            
            logger.info("✅ Parent-Child Retrieval System Initialized.")
        except Exception as e:
            msg = f"⚠️ Retriever init failed: {e}"
            logger.warning(msg)
            print(msg)
            self.retriever = None

    def delete_documents_by_source(self, source_filename: str):
        """Deletes all documents (Parent & Child) associated with a specific source filename."""
        try:
            from qdrant_client.http import models as rest_models
            
            logger.info(f"🗑️  Cleaning up existing vectors for: {source_filename}")
            
            # Delete from Qdrant (Child Chunks)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest_models.FilterSelector(
                    filter=rest_models.Filter(
                        must=[
                            rest_models.FieldCondition(
                                key="metadata.source",
                                match=rest_models.MatchText(text=source_filename)
                            )
                        ]
                    )
                )
            )
            
            # Note: We technically should also cleanup S3 Parent Store, but 
            # ParentDocumentRetriever manages mapping via doc_id. 
            # Since we generate new chunks/ids loosely, old S3 parent docs might be orphaned.
            # For now, vector cleanup is the critical part to prevent duplicate search results.
            
            logger.info(f"✅ Cleanup Complete for {source_filename}")
            
        except Exception as e:
            logger.error(f"Failed to delete existing documents for {source_filename}: {e}")

    def add_documents(self, documents):
        """Adds 'Parent' documents. The Retriever will auto-split them into Children."""
        if not documents:
            return
        
        try:
            logger.info(f"📤 Indexing {len(documents)} Parent Documents.")
            
            if self.retriever is None:
                self._initialize_components()
            
            if self.retriever:
                self.retriever.add_documents(documents)
                logger.info("✅ Indexing Complete.")
            else:
                logger.error("❌ Failed to initialize retriever for ingestion.")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            import traceback
            traceback.print_exc()

    def rewrite_query(self, query: str, chat_history: list = None) -> dict:
        """Refines the user query (Contextualized by History) and extracts filters."""
        try:
            # Construct History String
            history_str = ""
            if chat_history:
                # Limit to last 3 interactions to keep prompt small
                recent_history = chat_history[-6:] 
                for msg in recent_history:
                    role = "User" if msg.type == "human" else "Assistant"
                    history_str += f"{role}: {msg.content}\n"
            
            prompt_template = """You are an expert RAG query processor. 
                Your goal is to REWRITE the user's query into a STANDALONE technical query that effectively searches a Vector Database.

                **PHASE 1: CONTEXT RESOLUTION (CRITICAL)**
                - Use the CHAT HISTORY to resolve pronouns (e.g., "it", "this", "that report", "the previous answer").
                - If the user asks "How did you conclude this?" or "Why?", you MUST rewrite it to: "Reasoning for [Specific Claim from previous Assistant Answer]".
                - Example:
                    History: (Assistant: The noise limit is 45 dB.)
                    User: "Where is this mentioned?"
                    Rewritten: "Source of 45 dB noise limit in the documents"

                **PHASE 2: TRANSLATION & EXPANSION**
                - The documents are Multilingual (Swedish/German/English). 
                - Translate KEY technical terms into ALL 3 languages using OR logic.
                - Example: "Noise" -> "Noise OR buller OR Lärm"

                **PHASE 3: METADATA EXTRACTION**
                - If a specific filename is mentioned (e.g. "Nordborg"), extract it as a filter.
                
                **Rules:**
                - Return strictly JSON: {{"query": "final rewritten text", "filter": {{"key": "value"}} or null}}
                - Do NOT answer the question. Just rewrite.
                
                Chat History:
                {history}
                
                Current User Query: {query}
                JSON Output:"""
            
            prompt = PromptTemplate.from_template(prompt_template)
            chain = prompt | self.rewriter_llm
            result = chain.invoke({"query": query, "history": history_str})
            
            # Clean and parse JSON
            content = result.content.strip()
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            
            import json
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Query processing failed: {e}. Using original query.")
            return {"query": query, "filter": None}

    def get_relevant_docs(self, query, top_k=10, chat_history=None):
        """Hybrid Retrieval (Child Search -> Parent Fetch) + Reranking Loop"""
        
        # Initialize default metrics
        metrics = {
            "rewrite_seconds": 0.0,
            "retrieval_seconds": 0.0,
            "rerank_seconds": 0.0,
            "total_seconds": 0.0
        }
        
        try:
            if self.retriever is None:
                return [], metrics

            # Step 0: Query Rewriting (The Safety Net)
            rewritten_result = self.rewrite_query(query, chat_history) # Returns dict now
            
            refined_query = rewritten_result.get("query", query)
            meta_filter = rewritten_result.get("filter")
            
            # [CRITICAL HOTFIX] Disable Filtering to prevent Qdrant 400 Bad Request (Missing Index)
            # The Reranker is smart enough to filter irrelevant docs. Hard filtering is too fragile.
            if meta_filter:
                logger.warning(f"🚫 Disabling Metadata Filter ({meta_filter}) to avoid Qdrant Index Errors. Relying on Vector Search.")
                meta_filter = None

            logger.info(f"✍️  Original: '{query}' -> Rewritten: '{refined_query}'")

            # Step 1: Base Retrieval (Get Parent Documents)
            # Fetch 'candidate_k' (e.g. 30) instead of final 'top_k' (e.g. 5)
            candidate_k = self.config['retrieval'].get('candidate_k', 30)
            
            # Construct Search Kwargs
            search_kwargs = {"k": candidate_k}
            
            # Apply Qdrant Filter if explicit
            if meta_filter:
                # Assuming simple key-value for now (e.g. filename="reports.pdf")
                # QdrantVectorStore supports 'filter' arg in search_kwargs directly? 
                # Langchain Qdrant uses 'filter' or 'filters' depending on version? 
                # Safer: Use Qdrant 'Filter' object construction if needed, but dict usually works for exact match.
                # However, user asked for "CONTAINS".
                # langchain-qdrant usually maps kwargs['filter'] to a Qdrant Filter.
                # We will construct a minimal filter dict compatible with qdrant specific filtering if needed, 
                # but simplest is to trust LangChain's dict passing.
                # Constructing a standard Qdrant Filter for filename
                from qdrant_client.http import models as rest_models
                
                # Iterate filters
                conditions = []
                print(f"DEBUG: meta_filter raw: {meta_filter}")
                for k, v in meta_filter.items():
                    print(f"DEBUG: Processing filter key={k}, value={v} (type: {type(v)})")
                    
                    # [FIX] Handle LLM returning complex dict for 'CONTAINS'
                    if isinstance(v, dict):
                         if 'CONTAINS' in v:
                             v = v['CONTAINS']
                         elif 'value' in v:
                             v = v['value']
                         else:
                             # Fallback: Convert to string or take first value? 
                             # Let's stringify or warn. 
                             print(f"WARNING: Unknown dict structure for filter {k}: {v}")
                             v = str(v)

                    # Check if 'filename' or 'source'
                    # Check if 'filename' or 'source'
                    if k in ['filename', 'source']:
                        # Use 'MatchValue' or 'MatchText' (Full Text) depending on field.
                        # Since filenames are keyword-ish but user wants "contains", 'MatchText' is safer?
                        # Or 'MatchValue' if exact? The rewriter might return partial.
                        # Let's try explicit MatchText for partials.
                        try:
                            conditions.append(
                                rest_models.FieldCondition(
                                    key="metadata.source", # Mapping 'filename' to 'metadata.source'
                                    match=rest_models.MatchText(text=v)
                                )
                            )
                        except Exception as e_filter:
                            print(f"DEBUG: Filter construction failed for {k}={v}: {e_filter}")
                            raise e_filter
                
                if conditions:
                   q_filter = rest_models.Filter(must=conditions)
                   search_kwargs["filter"] = q_filter

            # Step 1: Base Retrieval
            import time
            start_retrieval = time.time()
            
            # Forcing k and filter
            self.retriever.search_kwargs = search_kwargs
            
            initial_parents = self.retriever.invoke(refined_query) 
            
            time_retrieval_fetch = time.time() - start_retrieval
            logger.info(f"🔍 Retrieved {len(initial_parents)} Parent Documents in {time_retrieval_fetch:.2f}s")
            
            if not initial_parents:
                return [], {}

            # Step 2: Reranking with Cohere (Multilingual)
            start_rerank = time.time()
            logger.info(f"🔄 Reranking {len(initial_parents)} parent documents with Cohere...")
            
            if not self.cohere_client:
                logger.warning("⚠️ Cohere not available, using documents as-is")
                final_docs = initial_parents[:top_k]
                time_rerank = 0.0
            else:
                try:
                    # Prepare documents for Cohere
                    doc_texts = [doc.page_content for doc in initial_parents]
                    
                    # Call Cohere Rerank API
                    rerank_response = self.cohere_client.rerank(
                        model="rerank-multilingual-v3.0",
                        query=query,  # Use ORIGINAL query, not rewritten (Cohere handles multilingual)
                        documents=doc_texts,
                        top_n=top_k,
                        return_documents=False  # We already have the docs
                    )
                    
                    time_rerank = time.time() - start_rerank
                    logger.info(f"⏱️ Cohere Reranking Time: {time_rerank:.2f}s")
                    
                    # Map reranked results back to original docs
                    final_docs = []
                    for result in rerank_response.results:
                        original_doc = initial_parents[result.index]
                        final_docs.append(original_doc)
                        
                except Exception as e:
                    logger.error(f"❌ Cohere reranking failed: {e}. Using top candidates.")
                    final_docs = initial_parents[:top_k]
                    time_rerank = time.time() - start_rerank
            
            # [METRICS]
            metrics = {
                "rewrite_seconds": 0.0, # Placeholder until we instrument rewrite_query
                "retrieval_seconds": time_retrieval_fetch,
                "rerank_seconds": time_rerank,
                "total_seconds": time.time() - start_retrieval
            }
                
            return final_docs, metrics
        
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
            import traceback
            traceback.print_exc()
            return [], metrics
            
    def clear(self):
        """Clears the collection and docstore"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Cleared Qdrant collection {self.collection_name}")
            
            # Clear S3 DocStore (Prefix)
            bucket_name = os.getenv("S3_BUCKET_NAME", "neel-rag-data-2026")
            prefix = "parent_store/"
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(bucket_name)
            bucket.objects.filter(Prefix=prefix).delete()
            logger.info("Cleared S3 DocStore")
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
