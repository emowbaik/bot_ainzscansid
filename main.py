import logging

from config.config import DISCORD_TOKEN
from bot.bot import bot
from bot.logging_config import setup_logging


# Setup logging
setup_logging()

logging.info("Starting bot...")
bot.run(DISCORD_TOKEN)
