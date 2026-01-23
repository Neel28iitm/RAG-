
import os
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force UTC in Env for good measure
os.environ['TZ'] = 'UTC'

# Load Envs Robust
from src.core.config import load_env_robust
load_env_robust("config/.env")
load_env_robust(".env")

def start_worker():
    print("🚀 Starting Celery Worker (Async Mode) on Windows...")
    try:
        # pool=solo is mandatory for Windows. INFO level to reduce noise
        subprocess.run(["celery", "-A", "src.worker.celery_app", "worker", "--loglevel=INFO", "--pool=solo"])
    except KeyboardInterrupt:
        print("Stopping worker...")

if __name__ == "__main__":
    start_worker()
