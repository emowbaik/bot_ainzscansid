import os
import json
import logging
import discord
import feedparser
import pymysql
import asyncio
from datetime import datetime
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
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        logging.info("Database connection successful")
        return conn
    except pymysql.MySQLError as e:
        logging.error(f"Database connection failed: {e}")
        return None

# Fungsi untuk memformat tanggal
def format_datetime(date_string):
    dt = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Fungsi untuk mendapatkan last_entry_id dari database
def get_last_entry_id():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT entry_id FROM entries ORDER BY published DESC LIMIT 1')
            result = cursor.fetchone()
            logging.info(f"Fetched last_entry_id: {result[0] if result else 'None'}")
            return result[0] if result else None
        except pymysql.MySQLError as e:
            logging.error(f"Failed to fetch last_entry_id: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")
    return None

# Fungsi untuk menyimpan entry_id dan published ke database
def set_last_entry_id(entry_id, published):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            formatted_published = format_datetime(published)
            cursor.execute(
                'INSERT INTO entries (entry_id, published) VALUES (%s, %s) ON DUPLICATE KEY UPDATE published=%s',
                (entry_id, formatted_published, formatted_published)
            )
            conn.commit()
            logging.info(f"Set entry_id {entry_id} with published date {formatted_published}")
        except pymysql.MySQLError as e:
            logging.error(f"Failed to save entry_id {entry_id} to database: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

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
            set_last_entry_id(new_entry.id, new_entry.published)
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
    if not check_feed.is_running():
        check_feed.start()  # Mulai pengecekan feed secara berkala jika belum berjalan

@bot.command(name='sendall')
async def send_all_entries(ctx):
    try:
        feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            author = entry.author if 'author' in entry else 'Unknown'
            published = entry.published if 'published' in entry else 'Unknown'

            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")

        await ctx.send("All entries have been sent to Discord.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

async def fetch_feed(url):
    return feedparser.parse(url)

bot.run(os.getenv('DISCORD_TOKEN'))