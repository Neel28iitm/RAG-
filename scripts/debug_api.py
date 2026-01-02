import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 1. Load Env
load_dotenv()

key = os.getenv("GOOGLE_API_KEY")

print("="*30)
print("DIAGNOSTIC TEST")
print("="*30)

if not key:
    print("❌ GOOGLE_API_KEY not found in environment variables.")
else:
    print(f"✅ GOOGLE_API_KEY found: {key[:5]}...{key[-5:]}")

# 2. Test Embedding
print("\nTesting Embedding Model...")
try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vector = embeddings.embed_query("Test string")
    print("✅ Embedding successful! Vector length:", len(vector))
except Exception as e:
    print("❌ Embedding failed:")
    print(e)
