import os
import discord
import asyncio
import logging
import openpyxl
import feedparser
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands
from .utils import generate_excel_report, send_to_discord
from lib.http.db_utils import save_project_report, get_project_reports
from openpyxl.utils import get_column_letter

# Load environment variables
load_dotenv()

# Fungsi untuk mengambil feed RSS
async def fetch_feed(url):
    return feedparser.parse(url)

class ReportCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        
    # Command untuk lapor proyek
    @bot.tree.command(name="lapor", description="Lapor proyek yang telah selesai.")
    @app_commands.describe(
        channel="Nama channel proyek (contoh: #proyek-1)",
        user="Tag diri sendiri (contoh: @pelapor)",
        role="Role tugas (contoh: @developer)",
        chapter="Chapter yang dilaporkan (contoh: Chapter 12)",
        owner="Owner proyek (contoh: @project-owner)"
    )
    async def lapor(
        interaction: discord.Interaction,
        channel: discord.TextChannel,  # Channel objek
        user: discord.Member,          # User objek
        role: discord.Role,            # Role objek
        chapter: str,
        owner: discord.Member          # Owner objek
    ):
        try:
            # Simpan nama dan ID ke database
            save_project_report(
                channel_id=channel.id,
                channel_name=channel.name,  # Nama channel
                user_id=user.id,
                user_name=user.name,        # Nama pelapor
                role_id=role.id,
                role_name=role.name,        # Nama role
                chapter=chapter,
                owner_id=owner.id,
                owner_name=owner.name,      # Nama owner
                reporter_id=interaction.user.id,
                reporter_name=interaction.user.name  # Nama pelapor
            )
            
            # Respon ke pengguna
            await interaction.response.send_message(
                f"Proyek berhasil dilaporkan:\n"
                f"**Channel:** {channel.mention} ({channel.name})\n"
                f"**Pelapor:** {user.mention} ({user.name})\n"
                f"**Role Tugas:** {role.mention} ({role.name})\n"
                f"**Chapter:** {chapter}\n"
                f"**Owner:** {owner.mention} ({owner.name})",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Terjadi kesalahan saat melaporkan proyek: {e}",
                ephemeral=True
            )
            
    @commands.command(name="output laporan")
    async def output_laporan(self, ctx, bulan: str):
        """
        Command to generate project reports in Excel format.
        Usage: /output_laporan bulan januari
        """
        # Map bulan ke angka
        bulan_mapping = {
            "januari": 1, "februari": 2, "maret": 3, "april": 4,
            "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
            "september": 9, "oktober": 10, "november": 11, "desember": 12
        }

        if bulan.lower() not in bulan_mapping:
            await ctx.send("Bulan yang dimasukkan tidak valid. Harap gunakan nama bulan dalam Bahasa Indonesia.")
            return

        bulan_angka = bulan_mapping[bulan.lower()]

        # Fetch reports from the database
        reports = get_project_reports(bulan_angka)

        if not reports:
            await ctx.send(f"Tidak ada laporan proyek untuk bulan {bulan.capitalize()}.")
            return

        # Generate Excel file
        file_name = f"laporan_proyek_{bulan.lower()}.xlsx"
        generate_excel_report(reports, file_name)

        # Send the Excel file to the user
        await ctx.send(file=discord.File(file_name))

        # Remove the file after sending
        os.remove(file_name)

# Setup commands untuk bot
def setup_commands(bot):
    setup(bot)
    bot.add_cog(ReportCommands(bot))
