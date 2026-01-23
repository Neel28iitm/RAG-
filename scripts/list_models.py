
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    print("📋 Listing Available Models...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ No API Key found.")
        return

    genai.configure(api_key=api_key)
    
    try:
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"❌ List Failed: {e}")

if __name__ == "__main__":
    main()
