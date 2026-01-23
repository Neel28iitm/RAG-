
import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv("config/.env")
load_dotenv(".env")

def main():
    model_name = "gemini-2.5-flash"
    print(f"🤖 Testing connection to: {model_name}")
    print(f"📅 Current Date (simulated): 2026-01-18")
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        print("⏳ Invoking model...")
        start = time.time()
        response = llm.invoke("Hello, are you online? Reply with 'Yes'.")
        end = time.time()
        
        print(f"✅ Success! Response: {response.content}")
        print(f"⏱️ Time taken: {end - start:.2f}s")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()
