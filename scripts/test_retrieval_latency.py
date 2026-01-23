
import os
import sys
import time
import asyncio
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.core.config import load_config, load_env_robust
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService

# Load Env
load_env_robust()
config = load_config("config/settings.yaml")

async def test_latency():
    print("🚀 Initializing Services...")
    
    # Measure Init Time
    t_start = time.time()
    retriever = RetrievalService(config)
    generator = GenerationService(config)
    t_init = time.time() - t_start
    print(f"✅ Services Initialized in {t_init:.2f}s")
    
    query = "In the paper 'Rail/wheel rolling noise generation due to parametric excitation,' Section 2 explains the time-domain model. How is the 'Roughness' of the rail and wheel incorporated into the model, and what is the role of the 'Hertzian contact spring'?"
    
    print(f"\n📝 Testing Query: {query}")
    
    # 1. Retrieval Latency
    t1 = time.time()
    docs, metrics = retriever.get_relevant_docs(query, top_k=5)
    t_retrieval = metrics['total_seconds']
    print(f"🔍 Retrieval Time: {metrics['retrieval_seconds']:.2f}s")
    print(f"🔄 Rerank Time:    {metrics['rerank_seconds']:.2f}s")
    print(f"📄 Retrieved {len(docs)} documents.")
    
    if not docs:
        print("❌ No documents retrieved.")
        return

    # Print Retrieved Chunks for Quality Check
    print("\n--- Retrieved Content Preview ---")
    for i, doc in enumerate(docs):
        print(f"\n[Chunk {i+1}] Source: {doc.metadata.get('source')} (Page {doc.metadata.get('page_label')})")
        print(f"Content: {doc.page_content[:300]}...") # Print first 300 chars
    print("---------------------------------")

    # 2. Generation Latency
    print("\n🤖 Generating Answer...")
    t2 = time.time()
    answer = generator.generate_answer(query, docs)
    t_generation = time.time() - t2
    print(f"⚡ Generation Time: {t_generation:.2f}s")
    
    print("\n--- Final Answer ---")
    print(answer)
    print("--------------------")
    
    print(f"\n📊 Summary:")
    print(f"Retrieval:  {t_retrieval:.2f}s")
    print(f"Generation: {t_generation:.2f}s")
    print(f"Total:      {t_retrieval + t_generation:.2f}s")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_latency())
