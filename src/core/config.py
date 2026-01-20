"""
Module: Config
Purpose: Centralized configuration loading.
"""
import os
import yaml
import logging
# Custom Robust Loader to handle Windows UTF-16 vs UTF-8 issues
def load_env_robust(path=".env"):
    if not os.path.exists(path):
        return
    
    content = None
    try:
        # Try UTF-8
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeError:
        try:
            # Try UTF-16 (Common on Windows PowerShell redirection)
            with open(path, 'r', encoding='utf-16') as f:
                content = f.read()
        except UnicodeError:
            # Fallback
             pass
             
    if content:
        # Manual parsing to bypass dotenv's brittle parser
        for line in content.splitlines():
             line = line.strip()
             if not line or line.startswith('#'): continue
             if '=' in line:
                 key, val = line.split('=', 1)
                 val = val.strip().strip("'").strip('"')
                 os.environ[key.strip()] = val

# Load Environment Variables (Robustly)
load_env_robust(".env")
load_env_robust("config/.env")

logger = logging.getLogger('app_logger')

def load_config(config_path="config/settings.yaml"):
    """Loads configuration from YAML file"""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        logger.info("Configuration loaded successfully.")
        return config
