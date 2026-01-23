
import requests
import json
import sys

# Default to internal docker name
url = "http://api:8000/api/v1/chat"

print(f"🧪 Testing API at {url}...")

payload = {
    "query": "What represents the sound insulation?",
    "user_id": "api_test_user",
    "top_k": 3
}

try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Response Received:")
        print(f"Answer: {data.get('answer')}")
        print("Sources:")
        for src in data.get('sources', []):
            print(f" - {src.get('filename')} (Page {src.get('page_number')})")
    else:
        print(f"❌ Error: {response.text}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Connection Failed: {e}")
    sys.exit(1)
