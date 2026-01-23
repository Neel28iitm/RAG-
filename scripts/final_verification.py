"""
FINAL VERIFICATION: Test system with Cohere API key fixed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.core.config import load_config

def final_verification():
    config = load_config()
    retriever = RetrievalService(config)
    generator = GenerationService(config)
    
    query = "What meteorological conditions are assumed for the predicted noise immission values?"
    
    print("="*100)
    print("🎯 FINAL VERIFICATION TEST - With Cohere API Key")
    print("="*100)
    print(f"\nQuery: {query}\n")
    
    # Run full pipeline 3 times
    results = []
    
    for i in range(3):
        print(f"\n{'='*100}")
        print(f"ATTEMPT {i+1}")
        print(f"{'='*100}")
        
        try:
            # Full retrieval
            docs, metadata = retriever.get_relevant_docs(query)
            
            print(f"\n📊 Retrieval Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
            
            if docs:
                # Generate answer
                answer = generator.generate_answer(query, docs)
                
                # Store result
                result = {
                    'num_docs': len(docs),
                    'top_source': docs[0].metadata.get('source', 'Unknown'),
                    'answer_preview': answer[:150],
                    'found_data': 'couldn\'t find' not in answer.lower()
                }
                results.append(result)
                
                print(f"\n✅ Retrieved {len(docs)} documents")
                print(f"📄 Top Source: {result['top_source']}")
                print(f"💬 Answer Preview: {result['answer_preview']}...")
                print(f"🎯 Data Found: {'YES ✅' if result['found_data'] else 'NO ❌'}")
            else:
                print("\n❌ NO DOCUMENTS RETRIEVED!")
                results.append({'found_data': False})
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({'found_data': False})
    
    # Final verdict
    print("\n" + "="*100)
    print("🏁 FINAL VERDICT")
    print("="*100)
    
    all_found = all(r.get('found_data', False) for r in results)
    all_same_source = len(set(r.get('top_source') for r in results if 'top_source' in r)) == 1
    
    if all_found and all_same_source:
        print("\n🎉 ✅ SUCCESS! System is DETERMINISTIC and CONSISTENT!")
        print(f"   - All 3 attempts found the data")
        print(f"   - All retrieved from same source: {results[0].get('top_source')}")
        print("\n✅ READY FOR PRODUCTION DEPLOYMENT!")
    elif all_found:
        print("\n⚠️  PARTIAL SUCCESS")
        print(f"   - All 3 attempts found data ✅")
        print(f"   - But different sources retrieved (minor variation)")
        print("\n🟡 Acceptable for production but monitor closely")
    else:
        print("\n❌ PROBLEM STILL EXISTS!")
        found_count = sum(1 for r in results if r.get('found_data', False))
        print(f"   - Only {found_count}/3 attempts found data")
        print("\n🔴 NOT READY - Further debugging needed")

if __name__ == "__main__":
    final_verification()
