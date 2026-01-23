
import requests
import json
import sys

# Target the Internal Service Name 'api'
# If running locally (outside docker), use 'localhost'
url = "http://api:8000/api/v1/chat"

print(f"------- API VERIFICATION -------")
print(f"Target URL: {url}")

payload = {
    "query": "What was the measured sound level at the facade when five waxing stations were forced, according to the Mora Skidgymnasium report?",
    "user_id": "api_verification_user",
    "top_k": 5
}

print(f"Payload: {json.dumps(payload, indent=2)}")
print("Sending Request... (Waiting for RAG)")

try:
    response = requests.post(url, json=payload, timeout=120)
    
    if response.status_code == 200:
        print("\n✅ API RESPONSE (HTTP 200):")
        # Print valid JSON for developer
        print(json.dumps(response.json(), indent=4))
    else:
        print(f"\n❌ ERROR (HTTP {response.status_code}):")
        print(response.text)

except Exception as e:
    print(f"\n❌ CONNECTION FAILED: {e}")
    # Fallback for local testing if internal DNS fails
    print("Tip: If running outside Docker, ensure URL is http://localhost:8000")
