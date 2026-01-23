
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.retrieval import RetrievalService
from qdrant_client import models

load_dotenv("config/.env")

async def main():
    print("🕵️‍♂️ Starting Root Cause Diagnosis...")
    config = load_config()
    retrieval_service = RetrievalService(config)
    client = retrieval_service.client
    collection_name = retrieval_service.collection_name

    # ---------------------------------------------------------
    # TEST 1: REWRITE QUERY LOGIC
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Query Rewriter...")
    user_query = "What was the measured sound level at the facade when five waxing stations were forced?"
    
    try:
        rewritten = retrieval_service.rewrite_query(user_query)
        print(f"   Input: '{user_query}'")
        print(f"   Output: {rewritten}")
        
        rewritten_text = rewritten.get("query", "").lower()
        if "valla" in rewritten_text:
            print("   ✅ PASS: Rewriter added 'valla' (Swedish term).")
        else:
            print("   ❌ FAIL: Rewriter did NOT add 'valla'.")
    except Exception as e:
        print(f"   ❌ ERROR: Rewriter failed: {e}")

    # ---------------------------------------------------------
    # TEST 2: CONTENT EXISTENCE IN QDRANT (CHUNKING CHECK)
    # ---------------------------------------------------------
    print("\n[TEST 2] Checking Qdrant Content for 'vallastation' (Ingestion Check)...")
    
    # We will verify if ANY chunk in the DB contains the substring 'valla'
    # This proves if ingestion/parsing actually kept the text.
    
    # Using specific scroll with filter is better than generic scroll
    try:
        # Search for "valla" text in page_content (this requires payload index or just brute force scroll)
        # Qdrant 'MatchText' on 'page_content' usually works if keyword indexing is on.
        # But to be safe, we'll scroll specifically documents from the Mora file first.
        
        # 2a. Find Mora File chunks
        print("   -> Listing chunks for source containing 'Mora'...")
        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.source",
                    match=models.MatchText(text="Mora")
                )
            ]
        )
        
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=100, # Check first 100 chunks
            with_payload=True
        )
        
        print(f"   -> Found {len(points)} chunks related to 'Mora'.")
        
        found_keyword = False
        target_keyword = "valla"
        
        for point in points:
            content = point.payload.get("page_content", "").lower()
            if target_keyword in content:
                print(f"   ✅ PASS: Found '{target_keyword}' in chunk ID {point.id}")
                print(f"      Snippet: {content[:100]}...")
                found_keyword = True
                break
        
        if not found_keyword:
            print(f"   ❌ FAIL: '{target_keyword}' NOT found in first 100 chunks of Mora file.")
            print("      Possible Causes: Parsing failed, Image not OCR'd, or Chunking cut it out.")
            
    except Exception as e:
        print(f"   ❌ ERROR checking content: {e}")

    # ---------------------------------------------------------
    # TEST 3: RETRIEVAL SIMULATION
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Retrieval with 'Vallastation'...")
    try:
        # Direct search with the SWEDISH term
        docs = retrieval_service.get_relevant_docs("vallastation", top_k=3)
        if docs:
            print(f"   ✅ PASS: Retrieved {len(docs)} documents for 'vallastation'.")
            for d in docs:
                print(f"      - {d.metadata.get('source')} (Score: N/A - Hybrid)")
                print(f"      📝 Content Snippet ( first 500 chars):")
                print(f"      {d.page_content[:500]}...")
                print("-" * 50)
        else:
            print("   ❌ FAIL: Zero results for 'vallastation'.")
            
    except Exception as e:
        print(f"   ❌ ERROR testing retrieval: {e}")

if __name__ == "__main__":
    asyncio.run(main())
