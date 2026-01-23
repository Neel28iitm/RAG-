@echo off
TITLE Gemini RAG Controller

echo ========================================================
echo 🚀 Starting Gemini RAG System
echo ========================================================
echo.

echo 1. Starting Celery Worker (Async Mode)...
:: Start worker in a new minimized window
start /min "Gemini RAG Worker" cmd /k "python scripts/start_worker_async_final.py"

echo 2. Waiting for Worker to initialize...
timeout /t 5 /nobreak >nul

echo 3. Starting Streamlit Application...
echo.
echo ========================================================
echo 🌐 App will open in your browser shortly.
echo ⚠️  DO NOT CLOSE THIS WINDOW (It runs the worker)
echo ========================================================
echo.

streamlit run src/streamlit_app.py
