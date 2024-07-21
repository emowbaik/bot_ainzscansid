import os
import json
import logging
import discord
import feedparser
from discord.ext import commands, tasks
from .utils import send_to_discord
from .logging_config import setup_logging

# Setup logging
setup_logging()

# Muat data dari file JSON untuk roles
with open('roles.json') as f:
    entries_data = json.load(f)

# Inisialisasi bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Fungsi untuk memeriksa feed dan mengirim update
@tasks.loop(minutes=1)
async def check_feed():
    try:
        feed = feedparser.parse(os.getenv('RSS_URL'))
        last_entry_id = getattr(bot, 'last_entry_id', None)
        new_feed = feedparser.parse(os.getenv('RSS_URL'))
        new_entry = new_feed.entries[0]

        if new_entry.id != last_entry_id:
            bot.last_entry_id = new_entry.id
            title = new_entry.title
            link = new_entry.link
            author = new_entry.author
            published = new_entry.published

            # Log info tentang entry baru
            logging.info(f"New entry found: {title}")

            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
    except Exception as e:
        logging.error(f"Error checking feed: {e}")

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    check_feed.start()  # Mulai pengecekan feed secara berkala

@bot.command(name='sendall')
async def send_all_entries(ctx):
    try:
        feed = feedparser.parse(os.getenv('RSS_URL'))
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
    except Exception as e:
        logging.error(f"An error occurred: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
