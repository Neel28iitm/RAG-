
import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import load_config
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from langchain_core.documents import Document

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_logger')

async def main():
    print("🚀 Starting Smart Chunking Verification...")
    
    # 1. Load Config
    config = load_config("config/settings.yaml")
    
    # Ensure test directories exist
    test_data_dir = Path("data/verify_test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Create a Mock "Parent" Document (Simulating what Ingestion produces)
    # We will skip actual PDF parsing to save time/cost and directly test the Splitter/Retriever logic
    print("\n--- 1. Simulating Parent Document Ingestion ---")
    
    long_text = "Content Start. " + ("This is a child chunk sentence. " * 30) + "Content End. "
    # Make it long enough to be split into multiple children (assuming child ~400 chars/tokens)
    # 30 sentences * ~30 chars = ~900 chars. Should result in 2-3 children.
    
    parent_doc = Document(
        page_content=long_text,
        metadata={"source": "test_verification.pdf", "page": 1}
    )
    
    print(f"Parent Doc Length: {len(long_text)} characters")
    
    # 3. Initialize Retrieval Service (which has the ParentDocumentRetriever)
    print("\n--- 2. Initializing Retrieval Service ---")
    retrieval_service = RetrievalService(config)
    
    # Clear previous test data if needed (optional)
    # retrieval_service.clear() 
    
    # 4. Add Document (Should trigger Parent Storage + Child Indexing)
    print("\n--- 3. Indexing Document ---")
    retrieval_service.add_documents([parent_doc])
    
    # 5. Verify local doc store
    print("\n--- 4. Verifying Local Doc Store ---")
    doc_store_path = Path("data/doc_store")
    files = list(doc_store_path.glob("*"))
    print(f"Files in data/doc_store: {len(files)}")
    if len(files) > 0:
        print("✅ SUCCESS: Parent documents stored locally.")
    else:
        print("❌ FAIL: No files found in doc_store.")
        
    # 6. Test Retrieval
    print("\n--- 5. Testing Retrieval ---")
    query = "child chunk sentence"
    results = retrieval_service.get_relevant_docs(query, top_k=1)
    
    if results:
        retrieved_doc = results[0]
        print(f"Retrieved Doc Length: {len(retrieved_doc.page_content)}")
        print(f"Retrieved Metadata: {retrieved_doc.metadata}")
        
        if len(retrieved_doc.page_content) == len(long_text):
            print("✅ SUCCESS: Retrieved FULL Parent Document!")
        else:
            print(f"⚠️ WARNING: Retrieved length ({len(retrieved_doc.page_content)}) != Original ({len(long_text)}). Check if it's returning child.")
    else:
        print("❌ FAIL: No documents retrieved.")

if __name__ == "__main__":
    asyncio.run(main())
