import os
from datetime import datetime
from dateutil import parser
import discord
import logging
import re
from fuzzywuzzy import fuzz
from lib.http.db_utils import save_pending_entry, is_role_blacklisted

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

# Fungsi untuk menentukan role mention berdasarkan title dari RSS feed
async def get_role_mention(bot, title):
    series_name = extract_series_name(title)
    guild = bot.get_guild(int(os.getenv('GUILD_ID')))

    if not guild:
        logging.error("Guild not found.")
        return ""

    roles = guild.roles
    best_match = None
    highest_score = 0

    for role in roles:
        cleaned_role_name = re.sub(r"[\"'’‘“”]", "", role.name)

        if len(cleaned_role_name.split()) == 1 or is_role_blacklisted(role.id):
            continue

        score = fuzz.partial_ratio(series_name.lower(), cleaned_role_name.lower())
        if score > highest_score:
            highest_score = score
            best_match = role

    # Jika cocok, return role yang ditemukan
    if best_match and highest_score > 99:
        logging.info(f"Matched existing role: {best_match.name} (score: {highest_score})")
        return best_match.mention

    # Jika tidak ada role cocok, buat role baru
    try:
        new_role = await guild.create_role(name=series_name, mentionable=True, reason="Auto-created by Sebas Tian - Iron Butler")
        logging.info(f"Created new role: {new_role.name}")
        return new_role.mention
    except Exception as e:
        logging.error(f"Failed to create role: {e}")
        return ""

# Fungsi untuk mengirim pesan ke Discord
async def send_to_discord(bot, title, link, published, author):
    role_mention = await get_role_mention(bot, title)
    if not role_mention:
        logging.error("No role mention found, cannot send message.")
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
            await channel.send(content=f"<@&1176850935117516840> | {role_mention} Read Now!", embed=embed, view=view)
        except discord.DiscordException as e:
            logging.error(f"Failed to send message: {e}")
    else:
        logging.error("Channel not found.")
