"""Logging configuration."""
import logging
import os
from datetime import datetime
from config.settings import LOG_LEVEL, LOG_FILE

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger('EthicalCapitalism')
    logger.info(f"Logging initialized at {datetime.now().isoformat()}")
    return logger