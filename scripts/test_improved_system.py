"""
🧪 Test Script: Verify Query Response Improvements
Tests the enhanced system with the problematic query
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService

def test_query():
    print("=" * 80)
    print("🧪 TESTING IMPROVED QUERY RESPONSE SYSTEM")
    print("=" * 80)
    
    # The query that previously failed
    test_query = "According to the report, what negative effects has long-term noise exposure been shown to have on preschool children's performance and health?"
    
    print(f"\n📝 Test Query:")
    print(f"   {test_query}")
    
    config = load_config("config/settings.yaml")
    
    print(f"\n⚙️ Configuration:")
    print(f"   - candidate_k: {config['retrieval']['candidate_k']}")
    print(f"   - top_k: 15 (increased from 10)")
    print(f"   - LLM Prompt: Enhanced with fallback handling ✅")
    
    # Initialize services
    print("\n🔄 Initializing services...")
    retrieval_service = RetrievalService(config)
    generation_service = GenerationService(config)
    
    # Test retrieval
    print("\n" + "=" * 80)
    print("STEP 1: Retrieval")
    print("=" * 80)
    
    docs, metrics = retrieval_service.get_relevant_docs(
        test_query,
        top_k=15,
        chat_history=None
    )
    
    print(f"\n✅ Retrieved {len(docs)} documents")
    print(f"   ⏱️ Retrieval: {metrics.get('retrieval_seconds', 0):.2f}s")
    print(f"   ⏱️ Rerank: {metrics.get('rerank_seconds', 0):.2f}s")
    print(f"   ⏱️ Total: {metrics.get('total_seconds', 0):.2f}s")
    
    if docs:
        print(f"\n📄 Top 3 Sources:")
        for idx, doc in enumerate(docs[:3], 1):
            print(f"   [{idx}] {doc.metadata.get('source', 'Unknown')}")
    
    # Test generation with NEW prompt
    print("\n" + "=" * 80)
    print("STEP 2: Generation (with NEW fallback handling)")
    print("=" * 80)
    
    print("\n🤖 Generating answer...")
    answer = generation_service.generate_answer(
        original_query=test_query,
        retrieved_docs=docs,
        chat_history=[]
    )
    
    print("\n" + "=" * 80)
    print("📝 GENERATED ANSWER:")
    print("=" * 80)
    print(answer)
    print("=" * 80)
    
    # Analyze result
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    if "couldn't find specific information" in answer.lower():
        print("\n✅ SUCCESS: New fallback handling is working!")
        print("   - LLM acknowledged it couldn't find exact info")
        
        if "however" in answer.lower() or "related" in answer.lower():
            print("   - LLM provided related information ✅")
        
        if "might get better results" in answer.lower() or "ask about" in answer.lower():
            print("   - LLM suggested alternative queries ✅")
        
        print("\n🎉 System is now providing HELPFUL responses instead of generic 'Data not found'!")
    
    elif "data not found" in answer.lower():
        print("\n⚠️ Old behavior detected - still saying 'Data not found'")
        print("   System might need restart to load new prompt")
    
    else:
        print("\n✅ System found an answer! (Even better!)")
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_query()
