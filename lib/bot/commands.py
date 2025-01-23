import os
import discord
import asyncio
import logging
import feedparser
from dotenv import load_dotenv
from typing import Union
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from .utils import send_to_discord
from lib.http.db_utils import save_project_report, get_reports_for_month, upsert_rate, get_all_rates, fetch_reports_by_month, fetch_all_rates
from .output_utils import generate_output_lapor, generate_output_rate

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
    async def list_entries(interaction: discord.Interaction, ctx):
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
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
    async def send_entry(interaction: discord.Interaction, ctx, index: int):
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
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
            await send_to_discord(bot, entry_id, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")
            await ctx.send(f"Artikel '{title}' telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"Error sending entry: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    # Command untuk mengirim semua artikel
    @bot.command(name='sendall')
    async def send_all_entries(interaction: discord.Interaction, ctx):

        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
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

    POSISI = [
    app_commands.Choice(name="Typesetter", value="Typesetter"),
    app_commands.Choice(name="English Translator", value="English Translator"),
    app_commands.Choice(name="China Translator", value="China Translator"),
]

    # Command untuk lapor proyek
    @bot.tree.command(name="lapor", description="Lapor proyek yang telah selesai.")
    @app_commands.describe(
        judul="Nama proyek atau judul komik (contoh: One Piece)",
        chapter="Kirim satu chapter per laporan (contoh: Chapter 12)",
        posisi="Pilih posisi Anda dalam proyek ini (contoh: Typesetter, English Translator)",
        tag="Tag seseorang (contoh: @user, @uploader)",
    )

    @app_commands.choices(
        posisi=POSISI
    )

    async def lapor(
        interaction: discord.Interaction,
        judul: str,
        chapter: str,
        posisi: app_commands.Choice[str],
        tag: Union[discord.Member, discord.Role]
    ):

        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812, #Demon Council
            1110199421687308349, #✧⁠◝Ejecutivo◜⁠✧
            989854043507687435, #TS - Ejecutivo
            989854801019932702 #TL - Ejecutivo
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
            return

        try:
            save_project_report(
                judul_name=judul,
                chapter=chapter,
                posisi_name=posisi.value,
                reporter_id=interaction.user.id,
                reporter_name=interaction.user.name
            )

            # Periksa apakah tag adalah Member atau Role
            if isinstance(tag, discord.Member):
                mention = tag.mention  # Mention member
                tag_type = "staff"
            elif isinstance(tag, discord.Role):
                mention = tag.mention  # Mention role
                tag_type = "role"
            else:
                await interaction.response.send_message("Tag yang diberikan tidak valid.", ephemeral=True)
                return

            await interaction.response.send_message(
                f"Proyek berhasil dilaporkan:\n"
                f"**Judul:** {judul}\n"
                f"**Chapter:** {chapter}\n"
                f"**Posisi:** {posisi.name}\n"
                f"**Pelapor:** {interaction.user.mention} ({interaction.user.name})\n"
                f"**Tag {tag_type}:** {mention}",
                ephemeral=False
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Terjadi kesalahan saat melaporkan proyek: {e}",
                ephemeral=True
            )

    # Command untuk output lapor proyek
    @bot.tree.command(name="output_lapor", description="Generate project report in Excel format")
    async def output_lapor(interaction: discord.Interaction, bulan: str):
        """
        Generate a project report for a specific month.
        :param interaction: The interaction object.
        :param bulan: Month for which the report is generated, e.g., "Januari".
        """

        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
            return

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
            filename = f"output_lapor_{bulan.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            filepath = generate_output_lapor(filename, f"Laporan {bulan.capitalize()}", reports)
            
            try:
                # Kirim file ke Discord
                await interaction.response.send_message(
                content=f"Laporan output_lapor untuk bulan {bulan.capitalize()} berhasil dibuat.",
                file=discord.File(filepath)
                )
                os.remove(filepath)  # Hapus file setelah dikirim

            except Exception as e:
                logging.exception("Error saat mengirim laporan ke Discord.")
                await interaction.response.send_message(f"Terjadi kesalahan saat mengirim laporan: {e}", ephemeral=True)
                raise e

        except Exception as e:
            logging.exception("Error saat membuat laporan.")
            await interaction.response.send_message(f"Terjadi kesalahan saat membuat laporan: {e}", ephemeral=True)
            raise e

    # Command untuk list rate setiap posisi
    @bot.tree.command(name="list_rate", description="list/daftar posisi dan rate")
    async def list_rate(interaction: discord.Interaction):
        """
        Command untuk menampilkan daftar posisi dan rate yang tersimpan di database.
        """
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
            return
        
        rates = get_all_rates()

        if rates is None:
            await interaction.response.send_message("Terjadi kesalahan saat mengambil data.")
            return

        if not rates:
            await interaction.response.send_message("Belum ada rate yang tersimpan.")
            return

        # Format hasil data menjadi string
        rate_list = "Daftar Rate:\n"
        for rate in rates:
            position = rate['position']
            rate_value = f"{rate['rate']:.1f}k"  # Format rate menjadi 2 desimal, lalu tambahkan 'k'
            rate_list += f"{position}: {rate_value}\n"

        await interaction.response.send_message(rate_list)

    # Command untuk add atau update rate setiap posisi
    @bot.tree.command(name="set_rate", description="mengatur atau memperbarui rate staff")
    async def set_rate(interaction: discord.Interaction, position: str, rate: float):
        """
        Command untuk mengatur atau memperbarui rate untuk posisi tertentu.
        :param interaction: Interaction command.
        :param position: Nama posisi.
        :param rate: Nilai rate yang akan diatur.
        """
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
            return
        
        # Validasi input
        if rate <= 0:
            await interaction.response.send_message("Rate harus bernilai positif.")
            return

        # Perbarui atau tambah rate
        success = upsert_rate(position, rate)

        if success:
            await interaction.response.send_message(f"Rate untuk posisi '{position}' berhasil diatur menjadi {rate}.")
        else:
            await interaction.response.send_message("Terjadi kesalahan saat menyimpan data.")

    # Command untuk output rate atau hasil pendapatan
    @bot.tree.command(name="output_rate", description="Menghasilkan laporan Excel untuk laporan user dalam  bulan tertentu.")
    async def output_rate(interaction: discord.Interaction, bulan: str):
        """
        Menghasilkan file Excel laporan jumlah laporan user dan total pendapatan berdasarkan rate per   posisi.
        """
        
        # ID role yang diizinkan
        ALLOWED_ROLE_IDS = {
            969063676734763009, #Supreme Beings
            969063133115191296, #Lucifer
            985182357915041812 #Demon Council
        }

        # Periksa apakah user memiliki salah satu role
        user_roles = {role.id for role in interaction.user.roles}
        if not ALLOWED_ROLE_IDS.intersection(user_roles):
            await interaction.response.send_message(
                "Anda tidak memiliki role yang diperlukan untuk menggunakan perintah ini.",
                ephemeral=True
            )
            return
        
        try:
            # Mapping nama bulan ke angka
            month_mapping = {
                "januari": 1, "februari": 2, "maret": 3, "april": 4,
                "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
                "september": 9, "oktober": 10, "november": 11, "desember": 12
            }
            month_number = month_mapping.get(bulan.lower())
            if not month_number:
                await interaction.response.send_message(
                    "Bulan tidak valid. Gunakan nama bulan dalam bahasa Indonesia.", ephemeral=True
                )
                return

            # Ambil data laporan dari database
            reports = fetch_reports_by_month(month_number)
            if not reports:
                await interaction.response.send_message(
                    f"Tidak ada laporan ditemukan untuk bulan {bulan}.", ephemeral=True
                )
                return

            # Hitung jumlah laporan per user dan total pendapatan
            user_report_count = {}
            position_rates = fetch_all_rates()  # Ambil rate posisi dari database
            total_pendapatan = {}

            for report in reports:
                reporter_name = report["reporter_name"]
                posisi_name = report["posisi_name"]

                # Tambahkan jumlah laporan
                user_report_count[reporter_name] = user_report_count.get(reporter_name, 0) + 1

                # Hitung total pendapatan
                rate = position_rates.get(posisi_name, 0)  # Default rate 0 jika posisi tidak ditemukan
                total_pendapatan[reporter_name] = total_pendapatan.get(reporter_name, 0) + rate

            # Buat file Excel
            filename = f"output_rate_{bulan.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            filepath = os.path.join("output", filename)

            # Pastikan folder 'output' ada
            os.makedirs("output", exist_ok=True)
            generate_output_rate(filepath, f"Laporan {bulan.capitalize()}", bulan, user_report_count,   total_pendapatan)

            # Kirim file ke Discord
            await interaction.response.send_message(
                content=f"Laporan output_rate untuk bulan {bulan.capitalize()} berhasil dibuat.",
                file=discord.File(filepath)
            )

            # Hapus file setelah dikirim
            os.remove(filepath)

        except Exception as e:
            await interaction.response.send_message(
                f"Terjadi kesalahan saat membuat laporan: {e}", ephemeral=True
            )

# Setup commands untuk bot
async def setup_commands(bot):
    await bot.add_cog(Report(bot))
    setup(bot)
