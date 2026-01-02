"""
Module: Config
Purpose: Centralized configuration loading.
"""
import os
import yaml
import logging

logger = logging.getLogger('app_logger')

def load_config(config_path="config/settings.yaml"):
    """Loads configuration from YAML file"""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        raise FileNotFoundError(f"Config file not found at {config_path}")
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        logger.info("Configuration loaded successfully.")
        return config
