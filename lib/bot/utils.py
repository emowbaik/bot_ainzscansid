import os
import json
import discord
import logging
import re
from datetime import datetime
from dateutil import parser
from openpyxl import Workbook
from openpyxl.styles import Alignment
from fuzzywuzzy import fuzz
from lib.http.db_utils import save_pending_entry
from openpyxl.utils import get_column_letter

# Muat data dari file JSON untuk roles
with open('roles.json') as f:
    entries_data = json.load(f)

# Fungsi untuk mengubah warna hex menjadi integer
def hex_to_int(hex_color):
    return int(hex_color.lstrip('#'), 16)

# Fungsi untuk menyederhanakan timestamp
def simplify_timestamp(timestamp):
    # Jika timestamp adalah objek datetime, ubah menjadi string
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()  # Mengubah datetime menjadi string ISO
    try:
        dt = parser.parse(timestamp)
        return dt.strftime('%d %B %Y, %H:%M %p')
    except Exception as e:
        logging.error(f"Failed to simplify timestamp: {e}")
        return "Invalid date"

# Fungsi untuk mengekstrak nama seri dari judul
def extract_series_name(title):
    # Misalnya, kita anggap nama seri adalah bagian dari judul sebelum "Chapter" atau "Episode"
    match = re.match(r'^(.*?)(?:Chapter \d+|Episode \d+)?$', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return title

# Fungsi untuk menentukan role mention berdasarkan title
def get_role_mention(title):
    series_name = extract_series_name(title)
    logging.info(f"Extracted series name: {series_name}")
    for entry in entries_data['entries']:
        if entry['title'].lower() == series_name.lower():
            logging.info(f"Found matching series: {entry['title']} with role: {entry['role']}")
            return entry['role']
    logging.info(f"No matching series found for: {series_name}")
    return ""

# Fungsi untuk mengirim pesan ke Discord dengan dua tombol
async def send_to_discord(bot, entry_id, title, link, published, author):
    role_mention = get_role_mention(title)
    
    if not role_mention:
        save_pending_entry(entry_id, published, title, link, author)
        return
    
    simplified_time = simplify_timestamp(published)
    embed = discord.Embed(
        title=title,
        color=hex_to_int("#78478C")
    )
    embed.set_footer(text=f"Posted by {author} • {simplified_time}")

    button1 = discord.ui.Button(label="Baca Sekarang", url=link, style=discord.ButtonStyle.link)
    button2 = discord.ui.Button(label="Visit Site", url="https://ainzscans.net/", style=discord.ButtonStyle.link)

    view = discord.ui.View()
    view.add_item(button1)
    view.add_item(button2)

    channel = bot.get_channel(int(os.getenv('TARGET_CHANNEL_ID')))  # Ganti dengan CHANNEL_ID target
    if channel:
        try:
            await channel.send(content=f"{role_mention} Read Now!", embed=embed, view=view)
        except discord.DiscordException as e:
            logging.error(f"Failed to send message: {e}")
    else:
        logging.error("Channel not found.")

def generate_excel_report(reports, file_name):
    """
    Generate an Excel report from project reports data.
    :param reports: List of reports from the database.
    :param file_name: Name of the output Excel file.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Laporan Proyek"

    # Header
    headers = ["ID", "Nama Channel", "Role Tugas", "Pelapor", "Owner", "Chapter", "Tanggal Lapor"]
    ws.append(headers)

    # Center align headers
    for col_num, _ in enumerate(headers, start=1):
        col_letter = get_column_letter(col_num)
        ws[f"{col_letter}1"].alignment = Alignment(horizontal="center", vertical="center")

    # Data rows
    for report in reports:
        ws.append([
            report["id"],
            report["channel_name"],  # Make sure this column is properly fetched
            report["role_name"],     # Make sure this column is properly fetched
            report["reporter_name"], # Make sure this column is properly fetched
            report["chapter"],
            report["reported_at"].strftime("%Y-%m-%d %H:%M:%S")
        ])

    # Auto-adjust column width
    for column in ws.columns:
        max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
        ws.column_dimensions[column[0].column_letter].width = max_length

    # Save the file
    wb.save(file_name)