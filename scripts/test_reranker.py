
from flashrank import Ranker, RerankRequest
import sys

def main():
    print("🧪 Testing FlashRank Models...")
    
    # Try loading a multilingual capable model
    # rank-T5-flan is often supported and better than TinyBERT
    model_name = "rank-T5-flan" 
    
    print(f"⏳ Attempting to load model: {model_name}")
    try:
        ranker = Ranker(model_name=model_name)
        print(f"✅ Successfully loaded {model_name}")
        
        # Test with dummy data
        query = "noise limits"
        passages = [
             {"id": "1", "text": "Bullergränser för trafik"},
             {"id": "2", "text": "Sound insulation values for walls"}
        ]
        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)
        print(f"✅ Rerank Success. Top result: {results[0]}")
        
    except Exception as e:
        print(f"❌ Failed to load {model_name}: {e}")
        print("ℹ️  Falling back to testing 'ms-marco-MiniLM-L-12-v2'...")
        try:
             ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
             print("✅ Successfully loaded ms-marco-MiniLM-L-12-v2")
        except Exception as e2:
             print(f"❌ Failed fallback: {e2}")

if __name__ == "__main__":
    main()
