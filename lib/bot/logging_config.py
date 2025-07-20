import os
import logging
from logging.handlers import RotatingFileHandler

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
level = getattr(logging, log_level, logging.INFO)

def setup_logging():
    handler = RotatingFileHandler('bot.log', maxBytes=1_000_000, backupCount=3)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            handler
        ]
    )
