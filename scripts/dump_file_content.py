
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.core.config import load_config
from src.app.retrieval import RetrievalService

def dump():
    load_dotenv()
    config = load_config()
    retrieval = RetrievalService(config) 
    
    print("dumping 25016_FME content...")
    
    # We want to fetch ALL chunks for this file.
    # Since we can't easily filter by metadata in this basic wrapper without scrolling,
    # we will search for the filename itself which usually appears in the header/footer text or metadata.
    # better: just search for "Utomhusfläkt" (part of filename) with high k
    
    query = "Utomhusfläkt"
    results = retrieval.retriever.vectorstore.similarity_search(query, k=50)
    
    with open("debug_25016_dump.txt", "w", encoding="utf-8") as f:
        for i, doc in enumerate(results):
            source = doc.metadata.get("source", "")
            if "25016" in source:
                f.write(f"--- Chunk {i} ---\n")
                f.write(f"Source: {source}\n")
                f.write(f"Page: {doc.metadata.get('page_label', '?')}\n")
                f.write(f"Content:\n{doc.page_content}\n")
                f.write("\n" + "="*50 + "\n")
    
    print("Dump complete to debug_25016_dump.txt")

if __name__ == "__main__":
    dump()
