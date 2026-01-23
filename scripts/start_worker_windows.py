
import os
import sys
import subprocess

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load Envs Robust
from src.core.config import load_env_robust
load_env_robust("config/.env")
load_env_robust(".env")

def start_worker():
    print("🚀 Starting Celery Worker on Windows (Pool=Solo)...")
    try:
        # Using shell=True to spawn correctly, and pool=solo for Windows compat
        subprocess.run(["celery", "-A", "src.worker.celery_app", "worker", "--loglevel=info", "--pool=solo"])
    except KeyboardInterrupt:
        print("Stopping worker...")

if __name__ == "__main__":
    start_worker()
