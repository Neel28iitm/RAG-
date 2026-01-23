import os
from dotenv import load_dotenv, find_dotenv

def check_env():
    print("🔍 Environment Variable Debugger")
    
    # 1. Find .env file
    env_path = find_dotenv()
    if not env_path:
        print("❌ .env file NOT found!")
        return
    else:
        print(f"✅ Found .env at: {env_path}")

    # 2. Load it
    load_dotenv(env_path, override=True)
    
    # 3. List all keys (Values hidden for security)
    print("\n--- Loaded Keys ---")
    keys_found = []
    qdrant_key_status = "MISSING"
    
    # Read file manually to see what's actually in text
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"File Content Preview (First 5 lines):")
        for i, line in enumerate(lines[:5]):
            print(f"{i+1}: {line.strip()}")
            if "QDRANT" in line:
                print(f"   >>> Found line with QDRANT: '{line.strip()}'")

    # Check Environment
    val = os.getenv("QDRANT_API_KEY")
    if val:
        qdrant_key_status = f"PRESENT (Length: {len(val)})"
    
    print(f"\n👉 QDRANT_API_KEY Status: {qdrant_key_status}")

if __name__ == "__main__":
    check_env()
