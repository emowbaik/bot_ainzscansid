import os
import logging
import discord
import feedparser
import asyncio
import re
from discord.ext import commands, tasks
from ..config.config import respon_code_loop
from .utils import send_to_discord, get_role_mention
from .logging_config import setup_logging
from .commands import setup as setup_commands
from lib.http.db_utils import (
    fetch_pending_entries, delete_pending_entry, delete_old, set_last_entry_id, setup_database, entry_already_processed, save_processed_entry
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

@tasks.loop(minutes=2)
async def check_pending_entries():
    logging.info("Checking for pending entries...")
    pending_entries = fetch_pending_entries()
    for entry in pending_entries:
        entry_id, published, title, link, author = entry
        role_mention = await get_role_mention(bot, title)
        if role_mention:
            await send_to_discord(bot, entry_id, title, link, published, author)
            delete_pending_entry(entry_id)
            delete_old()
        # else:
            # logging.info(f"Role for '{title}' not found yet. Will retry later.")

def extract_series_name(title):
    # Misalnya, kita anggap nama seri adalah bagian dari judul sebelum "Chapter" atau "Episode"
    match = re.match(r'^(.*?)(?:Chapter \d+|Episode \d+)?$', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return title

# Fungsi untuk memeriksa feed dan mengirim update
@tasks.loop(minutes=2)
async def check_feed():
    try:
        logging.info('Checking feed...')
        new_feed = await asyncio.wait_for(fetch_feed_with_retry(os.getenv('RSS_URL')), timeout=60)

        # Iterate through all entries in the feed
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

    except asyncio.TimeoutError:
        logging.error('Timeout while fetching the feed')
    except Exception as e:
        logging.error(f"Error checking feed: {e}")


# Event ketika bot siap
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    await  bot.tree.sync()

    # try:
    #     synced = await bot.tree.sync()  # Sinkronisasi slash commands
    #     print(f"Synced {len(synced)} commands.")
    # except Exception as e:
    #     print(f"Error syncing commands: {e}")

    if not respon_code_loop.is_running():
        respon_code_loop.start()
    if not check_feed.is_running():
        check_feed.start()
    if not check_pending_entries.is_running():
        check_pending_entries.start()

bot.run(os.getenv('DISCORD_TOKEN'))
