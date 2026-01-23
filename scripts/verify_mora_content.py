
import asyncio
import os
import sys
from dotenv import load_dotenv
from qdrant_client.http import models as rest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.config import load_config
from src.app.retrieval import RetrievalService

load_dotenv("config/.env")
load_dotenv(".env")

async def main():
    print("------- VERIFYING MORA CONTENT -------")
    config = load_config()
    retriever = RetrievalService(config)
    
    filename = "25016_FME - Utomhusfläkt_Mora.pdf"
    print(f"Target Filename: {filename}")
    
    # Bypassing Count check due to missing index
    print("Reading chunks matching 'valla' (Client-side filter)...")
    
    # Fetch broadly
    res = retriever.vector_store.similarity_search_with_score(
        query="valla",
        k=20, # Fetch more to have a chance
    )
    
    found = False
    for doc, score in res:
         src = doc.metadata.get("source", "")
         if "Mora" in src:
             print(f"--- MATCH FOUND in {src} ---\nSnippet: {doc.page_content[:500]}\n-----------------------")
             found = True
             # We can print all matches
             
    if found:
         print("✅ Content is accessible in Mora file.")
    else:
         print("❌ 'valla' keyword NOT found in top 20 chunks (or Mora file missing).")
         print("Top Results Source List:")
         for doc, score in res:
             print(f" - {doc.metadata.get('source')}")

if __name__ == "__main__":
    asyncio.run(main())
