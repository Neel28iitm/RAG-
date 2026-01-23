import requests
import json
import sys

BASE_URL = "http://api:8000/api/v1/stream"

def test_stream():
    query = "Explain the noise limits in Mora report briefly."
    payload = {
        "query": query,
        "user_id": "stream_tester",
        "session_id": "stream_session_01"
    }
    
    print(f"🌊 Testing Streaming Endpoint: {BASE_URL}")
    print(f"❓ Query: {query}\n")
    print("Simply outputting chunks as they arrive:\n")
    print("-" * 50)
    
    try:
        with requests.post(BASE_URL, json=payload, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    text = chunk.decode('utf-8')
                    sys.stdout.write(text)
                    sys.stdout.flush()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    print("\n" + "-" * 50)
    print("\n✅ Stream Finished.")

if __name__ == "__main__":
    test_stream()
