"""
Test if retrieval is deterministic for the same query
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.retrieval import RetrievalService
from src.core.config import load_config

def test_retrieval_determinism():
    config = load_config()
    retriever = RetrievalService(config)
    
    query = "What meteorological conditions are assumed for the predicted noise immission values?"
    
    print("="*80)
    print("TESTING RETRIEVAL DETERMINISM")
    print("="*80)
    print(f"\nQuery: {query}\n")
    
    results = []
    
    # Run 3 times
    for i in range(3):
        docs, metadata = retriever.get_relevant_docs(query)
        
        # Get top doc IDs
        doc_ids = []
        if docs:
            for doc in docs[:5]:  # Top 5
                source = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', 'Unknown')
                preview = doc.page_content[:100].replace('\n', ' ')
                doc_ids.append(f"{source}:p{page}:{preview}")
        
        results.append(doc_ids)
        print(f"\nAttempt {i+1}: Retrieved {len(docs)} docs")
        print(f"  Top doc: {doc_ids[0] if doc_ids else 'NONE'}")
    
    # Check if all results are identical
    print("\n" + "="*80)
    print("DETERMINISM CHECK")
    print("="*80)
    
    if results[0] == results[1] == results[2]:
        print("\n✅ RETRIEVAL IS DETERMINISTIC")
        print("   Same docs returned every time!")
    else:
        print("\n❌ RETRIEVAL IS NON-DETERMINISTIC!")
        print("   Different docs returned each time!")
        print("\n   Attempt 1 vs Attempt 2:")
        for j in range(min(3, len(results[0]), len(results[1]))):
            match = "✅" if results[0][j] == results[1][j] else "❌"
            print(f"     {match} Doc {j+1}: {results[0][j][:80]}...")

if __name__ == "__main__":
    test_retrieval_determinism()
