"""
Simplified Debug: Test query retrieval directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService

def main():
    print("=" * 80)
    print("🔍 Testing Query: Noise Exposure on Preschool Children")
    print("=" * 80)
    
    query = "According to the report, what negative effects has long-term noise exposure been shown to have on preschool children's performance and health?"
    
    config = load_config("config/settings.yaml")
    
    print(f"\n📝 Query: {query}")
    print(f"\n⚙️ Config:")
    print(f"   - candidate_k: {config['retrieval']['candidate_k']}")
    print(f"   - top_k: {config['retrieval']['top_k']}")
    
    # Initialize services
    print("\n🔄 Initializing Retrieval Service...")
    retrieval_service = RetrievalService(config)
    
    print("🔄 Initializing Generation Service...")
    generation_service = GenerationService(config)
    
    # Test retrieval
    print("\n" + "=" * 80)
    print("STEP 1: Testing Retrieval")
    print("=" * 80)
    
    try:
        docs, metrics = retrieval_service.get_relevant_docs(
            query, 
            top_k=config['retrieval']['top_k'],
            chat_history=None
        )
        
        print(f"\n✅ Retrieved {len(docs)} documents")
        print(f"   ⏱️ Retrieval Time: {metrics.get('retrieval_seconds', 0):.2f}s")
        print(f"   ⏱️ Rerank Time: {metrics.get('rerank_seconds', 0):.2f}s")
        
        if docs:
            print("\n📄 Top 3 Retrieved Documents:")
            print("-" * 80)
            for idx, doc in enumerate(docs[:3], 1):
                print(f"\n[{idx}] {doc.metadata.get('source', 'Unknown')}")
                print(f"    Content (first 300 chars):")
                print(f"    {doc.page_content[:300]}...")
                
                # Check for key terms
                content_lower = doc.page_content.lower()
                keywords = ["noise", "children", "preschool", "health", "performance", "exposure"]
                found = [k for k in keywords if k in content_lower]
                if found:
                    print(f"    ✅ Keywords found: {found}")
                else:
                    print(f"    ❌ No relevant keywords found")
        else:
            print("\n❌ NO DOCUMENTS RETRIEVED!")
            print("\nPossible reasons:")
            print("1. Query embeddings don't match any document embeddings")
            print("2. Query is too specific/complex")
            print("3. Relevant content not in database")
            return
            
    except Exception as e:
        print(f"\n❌ Retrieval ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test generation
    print("\n" + "=" * 80)
    print("STEP 2: Testing Generation")
    print("=" * 80)
    
    try:
        answer = generation_service.generate_answer(
            original_query=query,
            retrieved_docs=docs,
            chat_history=[]
        )
        
        print(f"\n📝 Generated Answer:")
        print("-" * 80)
        print(answer)
        print("-" * 80)
        
        # Check if answer is "Data not found"
        if "data not found" in answer.lower() or "not found" in answer.lower():
            print("\n⚠️ ISSUE IDENTIFIED: LLM says 'Data not found'")
            print("\nThis means:")
            print("✅ Retrieval is working (documents retrieved)")
            print("❌ Retrieved documents don't contain the specific answer")
            print("\nPOSSIBLE SOLUTIONS:")
            print("1. Increase candidate_k (40 → 60-80)")
            print("2. Increase top_k (10 → 15-20)")
            print("3. Simplify the query")
            print("4. Check if the information actually exists in your documents")
        else:
            print("\n✅ Answer generated successfully!")
            
    except Exception as e:
        print(f"\n❌ Generation ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Additional keyword search
    print("\n" + "=" * 80)
    print("STEP 3: Simpler Keyword Test")
    print("=" * 80)
    
    simple_queries = [
        "noise exposure children",
        "preschool health effects",
        "long-term noise"
    ]
    
    for sq in simple_queries:
        print(f"\n🔍 Testing: '{sq}'")
        try:
            docs_simple, _ = retrieval_service.get_relevant_docs(sq, top_k=3, chat_history=None)
            if docs_simple:
                print(f"   ✅ Found {len(docs_simple)} docs")
                print(f"   📄 Top source: {docs_simple[0].metadata.get('source', 'Unknown')}")
            else:
                print(f"   ❌ No docs found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("Debug Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
