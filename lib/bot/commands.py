import os
import discord
import asyncio
import logging
import feedparser
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from .utils import send_to_discord
from lib.http.db_utils import save_project_report, get_reports_for_month
from .report_utils import generate_excel_report

# Load environment variables
load_dotenv()

# Fungsi untuk mengambil feed RSS
async def fetch_feed(url):
    return feedparser.parse(url)

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# Setup bot commands
def setup(bot):
    # Command untuk menampilkan daftar artikel
    @bot.command(name='ls')
    async def list_entries(ctx):
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
            await send_to_discord(bot, entry_id, title, link, published, author)
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

    TIPE_KOMIK = [
    app_commands.Choice(name="General", value="general"),
    app_commands.Choice(name="Advance", value="advance"),
    app_commands.Choice(name="Titah", value="titah"),
]

    POSISI = [
    app_commands.Choice(name="Typesetter", value="typesetter"),
    app_commands.Choice(name="English Translator", value="english translator"),
    app_commands.Choice(name="China Translator", value="china translator"),
]

    # Command untuk lapor proyek
    @bot.tree.command(name="lapor", description="Lapor proyek yang telah selesai.")
    @app_commands.describe(
        judul="Nama proyek atau judul komik (contoh: One Piece)",
        chapter="Kirim satu chapter per laporan (contoh: Chapter 12)",
        tipe_komik="Pilih tipe komik (contoh: General, Advance, Titah)",
        posisi="Pilih posisi Anda dalam proyek ini (contoh: Typesetter, English Translator)",
        tag="Tag seseorang (contoh: @user, @uploader)",
    )
    @app_commands.choices(
        tipe_komik=TIPE_KOMIK,
        posisi=POSISI
    )
    async def lapor(
        interaction: discord.Interaction,
        judul: str,
        chapter: str,
        tipe_komik: app_commands.Choice[str],
        posisi: app_commands.Choice[str],
        tag: discord.Member,
    ):
        try:
            save_project_report(
                judul_name=judul,
                chapter=chapter,
                tipe_komik=tipe_komik.value,
                posisi_name=posisi.value,
                reporter_id=interaction.user.id,
                reporter_name=interaction.user.name
            )

            await interaction.response.send_message(
                f"Proyek berhasil dilaporkan:\n"
                f"**Judul:** {judul}\n"
                f"**Chapter:** {chapter}\n"
                f"**Tipe Komik:** {tipe_komik.name}\n"
                f"**Posisi:** {posisi.name}\n"
                f"**Pelapor:** {interaction.user.mention} ({interaction.user.name})\n"
                f"**Tag:** {tag.mention} ({tag.name})",
                ephemeral=False
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Terjadi kesalahan saat melaporkan proyek: {e}",
                ephemeral=True
            )
    # logging.exception("Error saat melaporkan proyek.")

    # Command untuk output lapor proyek
    @bot.tree.command(name="output", description="Generate project report in Excel format")
    async def output_report(interaction: discord.Interaction, bulan: str):
        """
        Generate a project report for a specific month.
        :param interaction: The interaction object.
        :param bulan: Month for which the report is generated, e.g., "Januari".
        """
        try:
            # Mapping nama bulan ke angka
            month_mapping = {
                "januari": 1, "februari": 2, "maret": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                "september": 9, "oktober": 10, "november": 11, "desember": 12
            }
            month_number = month_mapping.get(bulan.lower())
            if not month_number:
                await interaction.response.send_message("Bulan tidak valid. Gunakan nama bulan dalam bahasa Indonesia.", ephemeral=True)
                return

            # Ambil laporan dari database
            reports = get_reports_for_month(month_number)
            if not reports:
                await interaction.response.send_message(f"Tidak ada laporan untuk bulan {bulan}.", ephemeral=True)
                return

            # Generate laporan Excel
            filename = f"laporan_{bulan.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            filepath = generate_excel_report(filename, f"Laporan {bulan.capitalize()}", reports)

            try:
                # Kirim file ke Discord
                await interaction.response.send_message(
                content=f"Laporan untuk bulan {bulan.capitalize()} berhasil dibuat.",
                file=discord.File(filepath)
                )
            # os.remove(filepath)  # Hapus file setelah dikirim

            except Exception as e:
                logging.exception("Error saat mengirim laporan ke Discord.")
                await interaction.response.send_message("Terjadi kesalahan saat mengirim laporan.", ephemeral=True)
                raise e

        except Exception as e:
            logging.exception("Error saat membuat laporan.")
            await interaction.response.send_message("Terjadi kesalahan saat membuat laporan.", ephemeral=True)
            raise e

# Setup commands untuk bot
async def setup_commands(bot):
    await bot.add_cog(Report(bot))
    setup(bot)
