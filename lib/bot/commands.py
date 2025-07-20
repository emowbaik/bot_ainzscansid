import os
import discord
import asyncio
import logging
import feedparser
from dotenv import load_dotenv
from discord.ext import commands
from .utils import send_to_discord
from lib.http.db_utils import add_role_to_blacklist, remove_role_from_blacklist

# Load environment variables
load_dotenv()

# Fungsi untuk mengambil feed RSS
async def fetch_feed(url):
    return feedparser.parse(url)

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# Setup bot commands
def register_commands(bot):
    # Command untuk menampilkan daftar artikel
    @bot.command(name='ls')
    async def list_entries(ctx):
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in ctx.author.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await ctx.send(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True)
            return
        
        try:
            feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
            entries = feed.entries[:10]  # Ambil 10 artikel terbaru

            if not entries:
                await ctx.send("Tidak ada artikel yang ditemukan.")
                return

            entry_list = "\n".join([f"{i+1}. {entry.title}" for i, entry in enumerate(entries)])
            await ctx.send(f"Daftar artikel:\n{entry_list}\n\nGunakan perintah `!kirim <nomor>` untuk mengirim artikel yang dipilih.")

        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk mengirim artikel tertentu
    @bot.command(name='kirim')
    async def send_entry(ctx, index: int):
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in ctx.author.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await ctx.send(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True)
            return
        
        try:
            feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=60)
            entries = feed.entries[:10]  # Ambil 10 artikel terbaru
    
            if index < 1 or index > len(entries):
                await ctx.send("Nomor artikel tidak valid.")
                return
    
            entry = entries[index - 1]
            title = entry.title
            link = entry.link
            author = entry.get('author', 'Unknown')
            published = entry.get('published', 'Unknown')
            entry_id = entry.get('id', 'unknown-id')
    
            # Panggil fungsi send_to_discord dengan argumen lengkap
            await send_to_discord(ctx.bot, entry_id, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
            await ctx.send(f"Artikel '{title}' telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"Error sending entry: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk mengirim semua artikel
    @bot.command(name='sendall')
    async def send_all_entries(ctx):

        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in ctx.author.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await ctx.send(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True)
            return

        try:
            feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=60)
            entries = feed.entries[:10]  # Ambil 10 artikel terbaru
    
            if not entries:
                await ctx.send("Tidak ada artikel yang ditemukan untuk dikirim.")
                return
    
            for entry in entries:
                title = entry.title
                link = entry.link
                author = entry.author if 'author' in entry else 'Unknown'
                published = entry.published if 'published' in entry else 'Unknown'
    
                await send_to_discord(ctx.bot, title, link, published, author)
                logging.info(f"Successfully sent notification for: {title}")

            await ctx.send("Semua artikel telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"An error occurred while sending all entries: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk menyapa pengguna
    @bot.command(name='hi')
    async def halo(ctx):
        intro_message = (
            "Halo! Saya adalah bot yang dirancang untuk membantu mengirimkan notifikasi "
            "artikel terbaru dari RSS feed ke Discord. Anda bisa menggunakan command berikut:\n\n"
            "1. `!list` - Untuk menampilkan daftar artikel terbaru.\n"
            "2. `!send <nomor>` - Untuk mengirim artikel tertentu ke Discord.\n"
            "3. `!sendall` - Untuk mengirim semua artikel terbaru ke Discord.\n"
            "4. `!lapor` - Untuk melaporkan proyek yang telah selesai.\n\n"
            "Terima kasih telah menggunakan saya! 😊"
        )
        await ctx.send(intro_message)

    # command add_blacklist role dan remove_blacklist role
    @bot.command(name="add_blacklist_role")
    async def add_blacklist_role(ctx, role: discord.Role):
        if add_role_to_blacklist(role.id, role.name):
            await ctx.send(f"Role `{role.name}` berhasil ditambahkan ke daftar blacklist.")
        else:
            await ctx.send(f"Gagal menambahkan role `{role.name}` ke daftar blacklist.")

    @bot.command(name="remove_blacklist_role")
    async def remove_blacklist_role(ctx, role: discord.Role):
        if remove_role_from_blacklist(role.id):
            await ctx.send(f"Role `{role.name}` berhasil dihapus dari daftar blacklist.")
        else:
            await ctx.send(f"Gagal menghapus role `{role.name}` dari daftar blacklist.")

# Setup commands untuk bot
async def setup(bot):
    register_commands(bot)
