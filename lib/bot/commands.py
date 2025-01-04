import asyncio
import logging
import feedparser
from discord.ext import commands
from .utils import send_to_discord
from dotenv import load_dotenv
import os
import pymysql

# Load environment variables
load_dotenv()

# Fungsi untuk mengambil feed RSS
async def fetch_feed(url):
    return feedparser.parse(url)

# Fungsi untuk menyimpan laporan ke database
def save_report_to_db(reporter_id, reporter_name, channel_name, role_id, role_name, default_tag_id, default_tag_name):
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            db=os.getenv("DB_NAME"),
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO project_reports 
            (reporter_id, reporter_name, channel_name, role_id, role_name, default_tag_id, default_tag_name) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''',
            (reporter_id, reporter_name, channel_name, role_id, role_name, default_tag_id, default_tag_name)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error saving report to DB: {e}")

# Setup bot commands
def setup(bot):
    # Command untuk menampilkan daftar artikel
    @bot.command(name='list')
    async def list_entries(ctx):
        try:
            feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=30)
            entries = feed.entries[:10]  # Ambil 10 artikel terbaru

            if not entries:
                await ctx.send("Tidak ada artikel yang ditemukan.")
                return

            entry_list = "\n".join([f"{i+1}. {entry.title}" for i, entry in enumerate(entries)])
            await ctx.send(f"Daftar artikel:\n{entry_list}\n\nGunakan perintah `!send <nomor>` untuk mengirim artikel yang dipilih.")

        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk mengirim artikel tertentu
    @bot.command(name='send')
    async def send_entry(ctx, index: int):
        try:
            feed = await asyncio.wait_for(fetch_feed(os.getenv('RSS_URL')), timeout=60)
            entries = feed.entries[:10]  # Ambil 10 artikel terbaru
    
            if index < 1 or index > len(entries):
                await ctx.send("Nomor artikel tidak valid.")
                return
    
            entry = entries[index - 1]
            title = entry.title
            link = entry.link
            author = entry.author if 'author' in entry else 'Unknown'
            published = entry.published if 'published' in entry else 'Unknown'
    
            # Contoh pemanggilan send_to_discord
            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
            await ctx.send(f"Artikel '{title}' telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"Error sending entry: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk mengirim semua artikel
    @bot.command(name='sendall')
    async def send_all_entries(ctx):
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
    
                await send_to_discord(bot, title, link, published, author)
                logging.info(f"Successfully sent notification for: {title}")

            await ctx.send("Semua artikel telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"An error occurred while sending all entries: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk memberi laporan proyek selesai
    @bot.command(name='lapor')
    async def lapor(ctx, nama_channel: str, role_tugas: discord.Role, tag_default: discord.Member):
        try:
            # Validasi nama channel
            if not nama_channel.startswith("#"):
                await ctx.send("Format `nama-channel` salah. Harus diawali dengan `#`.")
                return

            # Ambil channel dari nama
            channel_name = nama_channel.lstrip("#")
            target_channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)

            if not target_channel:
                await ctx.send(f"Channel `{channel_name}` tidak ditemukan.")
                return

            # Simpan laporan ke database
            save_report_to_db(ctx.author.id, ctx.author.name, nama_channel,
                              role_tugas.id, role_tugas.name,
                              tag_default.id, tag_default.name)

            # Kirim laporan ke channel target
            laporan = (
                f"**Laporan Proyek Selesai:**\n"
                f"Channel: {nama_channel}\n"
                f"Role: {role_tugas.mention}\n"
                f"Tag Default: {tag_default.mention}\n"
                f"Reporter: {ctx.author.mention}"
            )
            await target_channel.send(laporan)

            # Konfirmasi ke pengguna yang melapor
            await ctx.send(f"Laporan berhasil dikirim ke {nama_channel} dan disimpan ke database.")

        except Exception as e:
            logging.error(f"Error saat mengirim laporan: {e}")
            await ctx.send("Terjadi kesalahan saat memproses laporan. Pastikan format sudah benar.")

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

# Setup commands untuk bot
def setup_commands(bot):
    setup(bot)
