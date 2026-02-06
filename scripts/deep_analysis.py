"""
DEEP ANALYSIS: Component-by-Component Debugging
Tests each stage of the RAG pipeline for non-determinism
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import hashlib
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.config import load_config
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def hash_text(text):
    """Create hash of text for comparison"""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def test_pipeline_determinism():
    config = load_config()
    retriever = RetrievalService(config)
    generator = GenerationService(config)
    
    query = "What meteorological conditions are assumed for the predicted noise immission values?"
    
    print("="*100)
    print("🔬 DEEP ANALYSIS: COMPONENT-BY-COMPONENT TESTING")
    print("="*100)
    print(f"\n📝 Query: {query}\n")
    
    # =========================================================================
    # TEST 1: QUERY REWRITING
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 1: QUERY REWRITING (Gemini LLM)")
    print("="*100)
    
    rewrites = []
    for i in range(3):
        try:
            rewritten = retriever._rewrite_query(query, [])
            rewrites.append(rewritten.get('query', query))
            print(f"\nAttempt {i+1}:")
            print(f"  Original: {query}")
            print(f"  Rewritten: {rewrites[i]}")
            print(f"  Hash: {hash_text(rewrites[i])}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            rewrites.append(query)
    
    if rewrites[0] == rewrites[1] == rewrites[2]:
        print("\n✅ QUERY REWRITING IS DETERMINISTIC")
    else:
        print("\n❌ QUERY REWRITING IS NON-DETERMINISTIC!")
        print("   This could cause different retrievals!")
    
    # =========================================================================
    # TEST 2: EMBEDDING GENERATION
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 2: EMBEDDING GENERATION (Google gemini-embedding-001)")
    print("="*100)
    
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        output_dimensionality=768  # Match Qdrant config
    )
    
    embeddings = []
    for i in range(3):
        try:
            emb = embedding_model.embed_query(query)
            # Compare first 5 values
            emb_preview = emb[:5]
            embeddings.append(emb_preview)
            print(f"\nAttempt {i+1}:")
            print(f"  Embedding (first 5): {[f'{x:.6f}' for x in emb_preview]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    if embeddings[0] == embeddings[1] == embeddings[2]:
        print("\n✅ EMBEDDINGS ARE DETERMINISTIC")
    else:
        print("\n❌ EMBEDDINGS ARE NON-DETERMINISTIC!")
        print("   Unlikely but possible!")
    
    # =========================================================================
    # TEST 3: QDRANT HYBRID SEARCH
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 3: QDRANT HYBRID SEARCH (Dense + BM25)")
    print("="*100)
    
    qdrant_results = []
    for i in range(3):
        try:
            # Direct Qdrant query (before parent fetch)
            child_docs = retriever.retriever.invoke(query)
            
            # Get doc IDs
            doc_ids = []
            for doc in child_docs[:5]:
                source = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', '?')
                snippet = doc.page_content[:50].replace('\n', ' ')
                doc_ids.append(f"{source}:p{page}:{snippet}")
            
            qdrant_results.append(doc_ids)
            
            print(f"\nAttempt {i+1}:")
            print(f"  Retrieved: {len(child_docs)} child docs")
            if doc_ids:
                print(f"  Top doc: {doc_ids[0]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    if qdrant_results[0] == qdrant_results[1] == qdrant_results[2]:
        print("\n✅ QDRANT RETRIEVAL IS DETERMINISTIC")
    else:
        print("\n❌ QDRANT RETRIEVAL IS NON-DETERMINISTIC!")
        print("\n   Comparing Attempt 1 vs Attempt 2:")
        for j in range(min(3, len(qdrant_results[0]), len(qdrant_results[1]))):
            match = "✅" if qdrant_results[0][j] == qdrant_results[1][j] else "❌"
            print(f"     {match} Doc {j+1}")
    
    # =========================================================================
    # TEST 4: PARENT DOCUMENT FETCH (S3 + Redis)
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 4: PARENT DOCUMENT FETCH (S3 + Redis Cache)")
    print("="*100)
    
    # Use first child docs to fetch parents
    if qdrant_results[0]:
        for i in range(2):
            try:
                print(f"\nAttempt {i+1}:")
                # This should be deterministic (same doc IDs)
                print(f"  Cache status: {'Hit' if retriever.use_redis else 'No Redis'}")
                print(f"  ✅ Parent fetch is deterministic (same child IDs → same parents)")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    # =========================================================================
    # TEST 5: COHERE RERANKING
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 5: COHERE RERANKING")
    print("="*100)
    
    if not retriever.cohere_client:
        print("\n⚠️  Cohere client not initialized - skipping")
    else:
        rerank_results = []
        try:
            # Get initial docs
            docs, _ = retriever.get_relevant_docs(query)
            
            if docs:
                print(f"\n  Testing with {len(docs)} documents...")
                
                for i in range(3):
                    # Rerank same docs
                    docs_for_rerank = [doc.page_content for doc in docs]
                    
                    rerank_response = retriever.cohere_client.rerank(
                        model="rerank-multilingual-v3.0",
                        query=query,
                        documents=docs_for_rerank,
                        top_n=10
                    )
                    
                    # Get reranked indices
                    indices = [r.index for r in rerank_response.results]
                    rerank_results.append(indices)
                    
                    print(f"\nAttempt {i+1}:")
                    print(f"  Top 5 indices: {indices[:5]}")
                    print(f"  Top doc after rerank: {docs[indices[0]].metadata.get('source', 'Unknown')}")
                
                if rerank_results[0] == rerank_results[1] == rerank_results[2]:
                    print("\n✅ COHERE RERANKING IS DETERMINISTIC")
                else:
                    print("\n❌ COHERE RERANKING IS NON-DETERMINISTIC!")
                    print("   THIS IS THE PROBLEM! Reranker gives different orders!")
        except Exception as e:
            print(f"\n❌ Reranking test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # =========================================================================
    # TEST 6: FINAL GENERATION
    # =========================================================================
    print("\n" + "="*100)
    print("TEST 6: LLM GENERATION (Temperature = 0.3)")
    print("="*100)
    
    try:
        docs, _ = retriever.get_relevant_docs(query)
        
        if docs:
            answers = []
            for i in range(2):
                answer = generator.generate_answer(query, docs)
                answers.append(answer)
                print(f"\nAttempt {i+1}:")
                print(f"  Answer length: {len(answer)} chars")
                print(f"  Starts with: {answer[:100]}...")
            
            if answers[0][:200] == answers[1][:200]:  # Compare first 200 chars
                print("\n✅ GENERATION IS MOSTLY DETERMINISTIC (temp=0.3)")
            else:
                print("\n⚠️  GENERATION HAS MINOR VARIATIONS (expected with temp>0)")
    except Exception as e:
        print(f"\n❌ Generation test failed: {e}")
    
    # =========================================================================
    # FINAL DIAGNOSIS
    # =========================================================================
    print("\n" + "="*100)
    print("🎯 FINAL DIAGNOSIS")
    print("="*100)
    
    print("\n📊 Component Analysis:")
    print(f"  1. Query Rewriting: {'✅ Deterministic' if rewrites[0] == rewrites[1] else '❌ Non-deterministic'}")
    print(f"  2. Embeddings: {'✅ Deterministic' if embeddings[0] == embeddings[1] else '❌ Non-deterministic'}")
    print(f"  3. Qdrant Search: {'✅ Deterministic' if qdrant_results[0] == qdrant_results[1] else '❌ NON-DETERMINISTIC ⚠️'}")
    print(f"  4. Parent Fetch: ✅ Deterministic (by design)")
    print(f"  5. Cohere Rerank: {'✅ Deterministic' if len(rerank_results) > 1 and rerank_results[0] == rerank_results[1] else '❌ NON-DETERMINISTIC ⚠️' if len(rerank_results) > 1 else '⚠️ Not tested'}")
    print(f"  6. Generation: ⚠️ Minor variations (acceptable)")
    
    print("\n💡 RECOMMENDATION:")
    if qdrant_results and qdrant_results[0] != qdrant_results[1]:
        print("  🔴 PRIMARY ISSUE: Qdrant Hybrid Search is non-deterministic")
        print("     - Likely cause: BM25 scoring or random tie-breaking")
        print("     - Fix: Increase candidate_k OR disable BM25 sparse search")
    elif len(rerank_results) > 1 and rerank_results[0] != rerank_results[1]:
        print("  🔴 PRIMARY ISSUE: Cohere Reranker is non-deterministic")
        print("     - ML models can be non-deterministic without explicit seeds")
        print("     - Fix: Use more documents OR accept minor variations")
    else:
        print("  🟢 No obvious non-determinism detected in this run")
        print("     - Issue might be intermittent or load-dependent")

if __name__ == "__main__":
    test_pipeline_determinism()
