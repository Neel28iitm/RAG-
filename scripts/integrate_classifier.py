"""
Simple integration script for query classification
Run this to add classifier to streamlit_app.py safely
"""
import re

# Read streamlit app
with open('src/streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import at top (after other imports)
import_line = "from src.app.query_classifier import QueryClassifier\n"
import_position = content.find("from src.app.generation import GenerationService")
if import_position > 0 and "query_classifier" not in content:
    next_line = content.find("\n", import_position) + 1
    content = content[:next_line] + import_line + content[next_line:]
    print("✅ Added QueryClassifier import")

# 2. Update load_services_cached to include classifier
old_return = """return (
            RetrievalService(cfg),
            GenerationService(cfg),
            DocumentIngestion(cfg) if 'ingestion' in cfg else None
        )"""

new_return = """return (
            RetrievalService(cfg),
            GenerationService(cfg),
            DocumentIngestion(cfg) if 'ingestion' in cfg else None,
            QueryClassifier()
        )"""

if old_return in content:
    content = content.replace(old_return, new_return)
    print("✅ Updated load_services_cached return")

# Update unpacking
old_unpack = "retrieval_service, generation_service, ingestion_service = load_services_cached()"
new_unpack = "retrieval_service, generation_service, ingestion_service, query_classifier = load_services_cached()"

if old_unpack in content:
    content = content.replace(old_unpack, new_unpack)
    print("✅ Updated service unpacking")

# 3. Add classification logic before retrieval
# Find the query handling section
search_pattern = r'with st\.spinner\("Searching\.\.\."\):'
match = re.search(search_pattern, content)

if match and "query_classifier.classify" not in content:
    insert_pos = match.start()
    
    classification_code = """                # Query Classification
                query_type = query_classifier.classify(prompt)
                
                if query_type == 'generic':
                    # Fast path - no retrieval
                    with st.spinner("Generating response..."):
                        import time
                        start = time.time()
                        response_text = generation_service.generate_generic_response(
                            prompt, chat_history=lc_history[-6:] if lc_history else []
                        )
                        elapsed = time.time() - start
                    
                    # Show metrics
                    with st.status("⚡ Performance (Generic Query)", expanded=False):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🔍 Retrieval", "0.00s", "Skipped")
                        c2.metric("🔄 Reranking", "0.00s", "Skipped")
                        c3.metric("⏱️ Total", f"{elapsed:.2f}s")
                    
                    st.markdown(response_text)
                    docs = []
                else:
                    # Full RAG pipeline
                """
    
    content = content[:insert_pos] + classification_code + content[insert_pos:]
    print("✅ Added classification logic")

# Write back
with open('src/streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n🎉 Integration complete!")
print("Now restart Streamlit to test")
