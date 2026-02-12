"""
Test script for async query API endpoints
Run this after starting:
1. Redis: docker run -d -p 6379:6379 redis
2. API: uvicorn api.main:app --reload
3. Worker: celery -A src.worker.celery_app worker --loglevel=info --pool=solo
"""
import requests
import time
import json

API_BASE = "http://localhost:8000"

def test_async_query():
    """Test async query workflow"""
    print("🧪 Testing Async Query API\n")
    
    # Step 1: Submit query
    print("Step 1: Submitting query...")
    query_data = {
        "query": "What is the noise level requirement for offices?",
        "top_k": 10
    }
    
    response = requests.post(f"{API_BASE}/query/async", json=query_data)
    
    if response.status_code != 200:
        print(f"❌ Failed to submit query: {response.text}")
        return
    
    result = response.json()
    task_id = result["task_id"]
    print(f"✅ Task submitted! ID: {task_id}")
    print(f"   Status: {result['status']}\n")
    
    # Step 2: Poll for results
    print("Step 2: Polling for results...")
    start_time = time.time()
    poll_count = 0
    
    while True:
        poll_count += 1
        elapsed = time.time() - start_time
        
        status_response = requests.get(f"{API_BASE}/query/status/{task_id}")
        
        if status_response.status_code != 200:
            print(f"❌ Failed to get status: {status_response.text}")
            break
        
        status_data = status_response.json()
        status = status_data["status"]
        progress = status_data["progress"]
        message = status_data.get("message", "")
        
        print(f"   Poll #{poll_count} ({elapsed:.1f}s): {status} - {progress}% - {message}")
        
        if status == "SUCCESS":
            print(f"\n✅ Query completed in {elapsed:.2f}s after {poll_count} polls!\n")
            print("📝 Answer:")
            print(f"   {status_data['answer'][:200]}...\n")
            print("📚 Sources:")
            for source in status_data.get("sources", [])[:3]:
                print(f"   - {source['document']}")
            print(f"\n⚡ Metrics:")
            metrics = status_data.get("metrics", {})
            for key, value in metrics.items():
                print(f"   {key}: {value}")
            break
        
        elif status == "FAILURE":
            print(f"\n❌ Query failed: {status_data.get('error')}")
            break
        
        # Wait 2 seconds before next poll
        time.sleep(2)
        
        # Timeout after 60 seconds
        if elapsed > 60:
            print("\n⏰ Timeout - query took too long")
            break

def test_concurrent_queries():
    """Test multiple concurrent queries"""
    print("\n\n🧪 Testing Concurrent Queries\n")
    
    queries = [
        "What is noise level for offices?",
        "What are reverberation time requirements?",
        "What standards apply to schools?"
    ]
    
    task_ids = []
    
    # Submit all queries
    print("Submitting 3 concurrent queries...")
    for i, query in enumerate(queries, 1):
        response = requests.post(
            f"{API_BASE}/query/async",
            json={"query": query, "top_k": 5}
        )
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            task_ids.append(task_id)
            print(f"  {i}. Task ID: {task_id}")
    
    print(f"\n✅ Submitted {len(task_ids)} tasks!\n")
    
    # Check all statuses
    print("Checking statuses after 5 seconds...")
    time.sleep(5)
    
    for i, task_id in enumerate(task_ids, 1):
        response = requests.get(f"{API_BASE}/query/status/{task_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"  {i}. Status: {data['status']} - Progress: {data['progress']}%")

if __name__ == "__main__":
    print("=" * 60)
    print("Async Query API Test")
    print("=" * 60 + "\n")
    
    # Test 1: Single async query
    test_async_query()
    
    # Test 2: Concurrent queries
    test_concurrent_queries()
    
    print("\n" + "=" * 60)
    print("✅ All tests complete!")
    print("=" * 60)
