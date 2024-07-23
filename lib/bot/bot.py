import os
import json
import logging
import discord
import feedparser
import asyncio
from discord.ext import commands, tasks
from .utils import send_to_discord
from .logging_config import setup_logging
from .commands import setup as setup_commands
from lib.http.db_utils import get_db_connection, get_last_entry_id, set_last_entry_id  # Import fungsi dari db_utils
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()

# Muat data dari file JSON untuk roles
with open('roles.json') as f:
    entries_data = json.load(f)

# Inisialisasi bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Setup custom commands
setup_commands(bot)

# Fungsi untuk memeriksa feed dan mengirim update
@tasks.loop(minutes=10)
async def check_feed():
    try:
        logging.info('Checking feed...')
        
        # Set a timeout for fetching the feed
        new_feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
        
        last_entry_id = get_last_entry_id()
        new_entry = new_feed.entries[0]

        if new_entry.id != last_entry_id:
            title = new_entry.title
            link = new_entry.link
            author = new_entry.author
            published = new_entry.published

            set_last_entry_id(new_entry.id, published, title, link, author)

            # Log info tentang entry baru
            logging.info(f"New entry found: {title}")

            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
        else:
            logging.info(f"No new entries found. Last entry ID {last_entry_id} is the same as the latest entry ID.")
    except asyncio.TimeoutError:
        logging.error('Timeout while fetching the feed')
    except Exception as e:
        logging.error(f"Error checking feed: {e}")


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    if not check_feed.is_running():
        check_feed.start()  # Mulai pengecekan feed secara berkala jika belum berjalan

async def fetch_feed(url):
    return feedparser.parse(url)

bot.run(os.getenv('DISCORD_TOKEN'))
