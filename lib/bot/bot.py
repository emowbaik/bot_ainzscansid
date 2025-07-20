import os
import logging
import discord
import feedparser
import asyncio
from discord.ext import commands, tasks
from ..config.config import respon_code_loop
from .utils import send_to_discord
from .logging_config import setup_logging
from .commands import register_commands as setup_commands
from lib.http.db_utils import (
    delete_old, setup_database,
    entry_already_processed, save_processed_entry
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()

# Inisialisasi bot dengan AutoShardedBot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.AutoShardedBot(command_prefix='!', intents=intents)

# Setup commands dan database
setup_commands(bot)
setup_database()

# Fungsi untuk mengambil feed menggunakan run_in_executor
async def fetch_feed(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, feedparser.parse, url)

# Fungsi untuk mengambil feed dengan retry logic
async def fetch_feed_with_retry(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            return await fetch_feed(url)
        except Exception as e:
            logging.error(f"Error fetching feed (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

# Fungsi utama: periksa feed dan kirim notifikasi
@tasks.loop(minutes=2)
async def check_feed():
    try:
        logging.info('Checking feed...')
        new_feed = await asyncio.wait_for(fetch_feed_with_retry(os.getenv('RSS_URL')), timeout=60)

        for entry in new_feed.entries:
            if not entry_already_processed(entry.id):
                title = entry.title
                link = entry.link
                author = entry.author
                published = entry.published

                save_processed_entry(entry.id, published, title, link, author)
                logging.info(f"New entry found: {title}")

                await send_to_discord(bot, entry.id, title, link, published, author)
                logging.info(f"Successfully sent notification for: {title}")

        # Jalankan task untuk menghapus entri lama
        if not delete_old.is_running():
                delete_old.start()

    except asyncio.TimeoutError:
        logging.error('Timeout while fetching the feed')
    except Exception as e:
        logging.error(f"Error checking feed: {e}")

# Event ketika bot siap
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    if not respon_code_loop.is_running():
        respon_code_loop.start()
    if not check_feed.is_running():
        check_feed.start()
