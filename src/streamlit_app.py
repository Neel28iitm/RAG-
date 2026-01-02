import streamlit as st
import asyncio
import os
import sys
import nest_asyncio
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv(dotenv_path="config/.env")

# Apply nest_asyncio
nest_asyncio.apply()

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger
from src.app.ingestion import DocumentIngestion
from src.app.retrieval import RetrievalService
from src.app.generation import GenerationService
from src.app.history import ChatHistoryManager
from src.core.config import load_config as core_load_config

# Setup Logger
logger = setup_logger('streamlit_logger')

def load_config(config_path="config/settings.yaml"):
    try:
        return core_load_config(config_path)
    except Exception as e:
        st.error(f"Config Error: {e}")
        st.stop()

# Initialize Services Cache
@st.cache_resource
def get_services():
    config = load_config()
    retrieval_service = RetrievalService(config)
    generation_service = GenerationService(config)
    history_manager = ChatHistoryManager() 
    return config, retrieval_service, generation_service, history_manager

async def run_ingestion(config, retrieval_service):
    with st.spinner("🚀 Analyzing Documents & Processing..."):
        try:
            ingestion = DocumentIngestion(config)
            if ingestion.should_clear_db:
                st.warning("🔄 Config change detected! Re-building Vector Database...")
                retrieval_service.clear()
            
            chunks = await ingestion.ingest_documents()
            
            if chunks:
                retrieval_service.add_documents(chunks)
                st.success(f"✨ Successfully processed {len(chunks)} new chunks!")
            else:
                st.info("No new documents found.")
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

def main():
    st.set_page_config(page_title="Gemini RAG", page_icon="✨", layout="wide")

    # --- CSS FOR GEMINI LOOK (LIGHT MODE) ---
    st.markdown("""
        <style>
        /* Light Theme Fixes */
        .stApp {
            background-color: #FFFFFF;
            color: #1F1F1F;
        }
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #F0F2F6;
            border-right: 1px solid #E0E0E0;
        }
        /* Buttons */
        .stButton button {
            background-color: #F0F2F6;
            color: #1F1F1F;
            border-radius: 20px;
            border: 1px solid #E0E0E0;
            transition: all 0.3s;
        }
        .stButton button:hover {
            background-color: #E0E0E0;
            color: #000;
        }
        /* Chat Input */
        .stChatInputContainer {
             background-color: #FFFFFF;
             border-radius: 25px;
             border: 1px solid #E0E0E0;
             box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
        }
        /* Titles */
        h1, h2, h3 {
            font-family: 'Google Sans', sans-serif;
            color: #1F1F1F;
        }
        </style>
    """, unsafe_allow_html=True)

    # Load Services
    try:
        config, retrieval_service, generation_service, history_manager = get_services()
    except Exception as e:
        st.error(f"Failed to initialize services: {e}")
        st.stop()

    # --- SESSION MANAGEMENT ---
    if "current_session_id" not in st.session_state:
        # Create default session if none exists
        st.session_state.current_session_id = history_manager.create_session()

    # --- SIDEBAR (HISTORY) ---
    with st.sidebar:
        st.title("Gemini RAG")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.current_session_id = history_manager.create_session()
            st.rerun()

        st.divider()
        st.markdown("**Recent**")
        
        # List Sessions
        sessions = history_manager.get_all_sessions()
        for s_id, data in sessions:
            title = data.get("title", "New Chat")
            # Highlight current session
            if s_id == st.session_state.current_session_id:
                title = f"🔵 **{title}**"
            
            if st.button(title, key=s_id, use_container_width=True):
                st.session_state.current_session_id = s_id
                st.rerun()

        st.divider()
        with st.expander("🛠️ Admin / Settings"):
            if st.button("🔄 Re-Ingest Documents"):
                asyncio.run(run_ingestion(config, retrieval_service))
            
            key = os.getenv("GOOGLE_API_KEY", "")
            if key.startswith("AIza"):
                 st.caption(f"🔑 Key Active: ...{key[-4:]}")

    # --- MAIN CHAT AREA ---
    current_session = history_manager.get_session(st.session_state.current_session_id)
    if not current_session:
        st.error("Session not found. creating new one.")
        st.session_state.current_session_id = history_manager.create_session()
        st.rerun()

    messages = current_session["messages"]

    # Welcome Screen if Empty
    if not messages:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h1 style='font-size: 3em; background: -webkit-linear-gradient(45deg, #4285F4, #9B72CB, #D96570); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                    Hello, Neel
                </h1>
                <h3 style='color: #666;'>How can I help you analyze your documents today?</h3>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # Render History
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    from langchain_core.messages import HumanMessage, AIMessage

    # Chat Input
    prompt = st.chat_input("Ask Gemini RAG...")

    if prompt:
        # 1. User Message
        with st.chat_message("user"):
            st.markdown(prompt)
        history_manager.add_message(st.session_state.current_session_id, "user", prompt)

        # 2. Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Prepare History
                    lc_history = []
                    for msg in current_session["messages"]:
                        if msg["role"] == "user":
                            lc_history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            lc_history.append(AIMessage(content=msg["content"]))

                    # RAG Pipeline
                    expanded = generation_service.expand_query(prompt)
                    
                    # Use FlashRank Re-ranking (Same as run.py)
                    docs = retrieval_service.get_relevant_docs(expanded, top_k=5)
                    
                    if not docs:
                        response_text = "I couldn't find relevant info."
                    else:
                        response_text = generation_service.generate_answer(prompt, docs, chat_history=lc_history)

                    st.markdown(response_text)
                    
                    # Save AI Message
                    history_manager.add_message(st.session_state.current_session_id, "assistant", response_text)
                    
                    # Rerun to update title in sidebar if new chat
                    if len(messages) <= 2:
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
