import sys
import os
import yaml
from langchain_core.documents import Document

# Fix path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_engine.generation import GenerationService
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

def load_config():
    with open("config/settings.yaml", 'r') as f:
        return yaml.safe_load(f)

def test_generation():
    print("🚀 Testing Generation...")
    config = load_config()
    
    try:
        gen_service = GenerationService(config)
        
        query = "What is the revenue?"
        docs = [Document(page_content="Revenue is $10M.", metadata={"source": "test.pdf"})]
        
        print(f"Query: {query}")
        
        # Test expand first
        expanded = gen_service.expand_query(query)
        print(f"Expanded: {expanded}")
        
        # Test generate
        answer = gen_service.generate_answer(query, docs)
        print(f"Answer: {answer}")
        
    except Exception as e:
        print(f"❌ ERROR CAUGHT IN SCRIPT: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
