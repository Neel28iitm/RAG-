"""
Debug script to test retrieval consistency
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.retrieval import RetrievalService
from src.core.config import load_config

def test_retrieval_consistency():
    config = load_config()
    retriever = RetrievalService(config)
    
    query = "What meteorological conditions are assumed for the predicted noise immission values?"
    
    print("=" * 80)
    print("TESTING RETRIEVAL CONSISTENCY")
    print("=" * 80)
    print(f"\nQuery: {query}\n")
    
    # Run retrieval 3 times
    for i in range(3):
        print(f"\n{'='*80}")
        print(f"ATTEMPT {i+1}")
        print(f"{'='*80}")
        
        try:
            docs, metadata = retriever.get_relevant_docs(query)
            
            print(f"\n✅ Retrieved {len(docs)} documents")
            print(f"\n📊 Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            if docs:
                print(f"\n📄 Top Document:")
                print(f"  Source: {docs[0].metadata.get('source', 'Unknown')}")
                print(f"  Page: {docs[0].metadata.get('page', 'Unknown')}")
                print(f"  Content Preview: {docs[0].page_content[:200]}...")
            else:
                print("\n❌ NO DOCUMENTS RETRIEVED!")
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_retrieval_consistency()
