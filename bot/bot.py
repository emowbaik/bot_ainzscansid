import os
import json
import logging
import discord
import feedparser
import pymysql
import asyncio
from discord.ext import commands, tasks
from .utils import send_to_discord
from .logging_config import setup_logging
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

# Fungsi untuk mendapatkan koneksi database
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

# Fungsi untuk mendapatkan last_entry_id dari database
def get_last_entry_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT last_entry_id FROM feed WHERE id=1')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Fungsi untuk menyimpan last_entry_id ke database
def set_last_entry_id(entry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO feed (id, last_entry_id) VALUES (1, %s) ON DUPLICATE KEY UPDATE last_entry_id=%s', (entry_id, entry_id))
    conn.commit()
    conn.close()

# Fungsi untuk memeriksa feed dan mengirim update
@tasks.loop(minutes=1)
async def check_feed():
    try:
        logging.info('Checking feed...')
        
        # Set a timeout for fetching the feed
        new_feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
        
        last_entry_id = get_last_entry_id()
        new_entry = new_feed.entries[0]

        if new_entry.id != last_entry_id:
            set_last_entry_id(new_entry.id)
            title = new_entry.title
            link = new_entry.link
            author = new_entry.author
            published = new_entry.published

            # Log info tentang entry baru
            logging.info(f"New entry found: {title}")

            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
    except asyncio.TimeoutError:
        logging.error('Timeout while fetching the feed')
    except Exception as e:
        logging.error(f"Error checking feed: {e}")

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    check_feed.start()  # Mulai pengecekan feed secara berkala

@bot.command(name='sendall')
async def send_all_entries(ctx):
    try:
        feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            author = entry.author if 'author' in entry else 'Unknown'
            published = entry.published if 'published' in entry else 'Unknown'

            # Log info tentang entry yang dikirim
            logging.info(f"Processing entry: {title}")

            # Periksa apakah title ada di JSON
            if any(e['title'].lower() == title.lower() for e in entries_data['entries']):
                await send_to_discord(bot, title, link, published, author)
                logging.info(f"Successfully sent notification for: {title}")

        await ctx.send("All entries have been sent to Discord.")
    except asyncio.TimeoutError:
        logging.error('Timeout while fetching the feed')
    except Exception as e:
        logging.error(f"An error occurred: {e}")

async def fetch_feed(url):
    return feedparser.parse(url)

bot.run(os.getenv('DISCORD_TOKEN'))
