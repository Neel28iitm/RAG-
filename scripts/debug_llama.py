import os
import sys
from dotenv import load_dotenv
from llama_parse import LlamaParse

# Force UTF-8 (optional, but good practice)
sys.stdout.reconfigure(encoding='utf-8')

# Load Env
load_dotenv()

print("="*40)
print("LLAMA CLOUD DEBUGGER")
print("="*40)

key = os.getenv("LLAMA_CLOUD_API_KEY", "")
google_key = os.getenv("GOOGLE_API_KEY", "")

# 1. Check Key Format
if not key:
    print("[ERROR] LLAMA_CLOUD_API_KEY is Empty/Missing!")
else:
    print(f"[OK] Loaded Key: '{key[:4]}...{key[-4:]}'")
    print(f"     Length: {len(key)}")
    if key.startswith("llx-"):
        print("     Prefix (llx-) looks correct.")
    else:
        print("[WARNING] Key does doesn't start with 'llx-'. It might be invalid.")

if not google_key:
    print("[ERROR] GOOGLE_API_KEY is Empty/Missing!")
else:
    print(f"[OK] Loaded Google Key: '{google_key[:4]}...{google_key[-4:]}'")

# 2. Test Connection (Minimal)
print("\nTesting LlamaParse Initialization...")
try:
    parser = LlamaParse(
        api_key=key, 
        result_type="markdown", 
        verbose=True
    )
    print("[OK] LlamaParse Object Initialized")
except Exception as e:
    print(f"[ERROR] Initialization Failed: {e}")

# 3. Warning about Quotes
print("\n[TIP] Ensure your .env file does NOT have quotes around the key.")
print("      Correct: LLAMA_CLOUD_API_KEY=llx-1234...")
print("      Wrong:   LLAMA_CLOUD_API_KEY=\"llx-1234...\"")
