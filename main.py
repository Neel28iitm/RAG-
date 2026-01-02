import os
import sys

def main():
    print("🚀 Starting Gemini RAG Application...")
    print("Use specific commands to run parts of the app:")
    print("1. Run Streamlit App: 'python main.py run'")
    print("2. Re-ingest Data:  'python main.py ingest'")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "run":
            print("running streamlit...")
            os.system("streamlit run src/streamlit_app.py")
            
        elif command == "ingest":
            print("running ingestion script...")
            # We need to make sure reingest script also uses new structure. 
            # Ideally we refactor reingest.py as well, but for now let's point to it if valid
            # Or better, trigger it via python
            # Since I haven't refactored scripts/reingest.py yet, it might fail. I should fix it.
            os.system("python scripts/reingest.py")
            
    else:
        print("\nDefaulting to launch Streamlit app...")
        os.system("streamlit run src/streamlit_app.py")

if __name__ == "__main__":
    main()
