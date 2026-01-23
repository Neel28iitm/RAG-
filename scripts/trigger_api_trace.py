
import requests
import json

def trigger_trace():
    url = "http://api:8000/api/v1/chat"
    payload = {
        "query": "What was the measured sound level at the facade when five waxing stations were forced?",
        "user_id": "trace_tester",
        "session_id": "trace_session_01",
        "top_k": 5
    }
    
    print(f"🚀 Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Response Received!")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Verification Failed: {e}")

if __name__ == "__main__":
    trigger_trace()
