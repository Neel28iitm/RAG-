
try:
    from langchain_qdrant import FastEmbedSparse
    print("✅ FastEmbedSparse imported successfully!")
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    
try:
    from langchain_qdrant import QdrantVectorStore
    print("✅ QdrantVectorStore imported successfully!")
except ImportError as e:
    print(f"❌ Import Failed: {e}")

import fastembed
print(f"✅ fastembed version: {fastembed.__version__}")
