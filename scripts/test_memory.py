import requests
import json
import uuid
import time

BASE_URL = "http://api:8000/api/v1/chat"
SESSION_ID = f"test_mem_{uuid.uuid4().hex[:8]}"

def chat(query):
    payload = {
        "query": query,
        "user_id": "tester",
        "session_id": SESSION_ID
    }
    try:
        response = requests.post(BASE_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"\n👤 User: {query}")
        print(f"🤖 AI: {data['answer']}")
        if data['sources']:
            print(f"   (Source: {data['sources'][0]['filename']})")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"🧠 Testing Conversational Memory (Session: {SESSION_ID})")
print("-" * 50)

# Turn 1: Context Setting
chat("Who is the 'Project Manager' mentioned in the Mora Skidgymnasium report?")

# Turn 2: Context Dependent (Pronoun Reference)
# AI should know 'he/she' refers to the Project Manager from Turn 1
chat("What is his/her email address?")

print("-" * 50)
print("✅ Test Complete. Check if the second answer correctly identified the person.")
