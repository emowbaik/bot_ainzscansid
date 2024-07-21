import os
import json
from dateutil import parser
import discord
import logging

# Muat data dari file JSON untuk roles
with open('roles.json') as f:
    entries_data = json.load(f)

# Fungsi untuk mengubah warna hex menjadi integer
def hex_to_int(hex_color):
    return int(hex_color.lstrip('#'), 16)

# Fungsi untuk menyederhanakan timestamp
def simplify_timestamp(timestamp):
    dt = parser.parse(timestamp)
    return dt.strftime('%d %B %Y, %H:%M %p')

# Fungsi untuk menentukan role mention berdasarkan title
def get_role_mention(title):
    for entry in entries_data['entries']:
        if entry['title'].lower() in title.lower():
            return entry['role']
    return ""

# Fungsi untuk mengirim pesan ke Discord dengan dua tombol
async def send_to_discord(bot, title, link, published, author):
    # Periksa apakah title ada di JSON
    if not any(entry['title'].lower() == title.lower() for entry in entries_data['entries']):
        logging.info(f"Title '{title}' not found in roles.json. Skipping...")
        return
    
    simplified_time = simplify_timestamp(published)
    embed = discord.Embed(
        title=title,
        color=hex_to_int("#78478C")
    )
    embed.set_footer(text=f"Posted by {author} • {simplified_time}")

    # Set image
    image_url = "https://images-ext-1.discordapp.net/external/vEu93IBiGC0IkfvvM8qEG1BQAMW48Yb7hxPohiY4Kzo/https/blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgM3omq_vH_U9a7yb-2B6bPkxkunGCB-GzGc6kY-KtACdDZ1EkzRNX4Ghr1yWU4kpPGfbUPIaxHuOe6S6rZ4X8RIHC7sU5V-s9o_1J83WR-0NwfPrbOJn05RwGxCGmzjGTsLwpKXg_S9e5LM7PbIyvOjK2eUrR6iGHK_928fBJdyyF1np_xUbAMkLAd/s1600/20230415_100900.jpg?format=webp&width=1022&height=377"
    embed.set_image(url=image_url)  # Gambar besar di dalam embed

    # Buat tombol
    button1 = discord.ui.Button(label="Baca Sekarang", url=link, style=discord.ButtonStyle.link)
    button2 = discord.ui.Button(label="Visit Site", url="https://ainzscans.net/", style=discord.ButtonStyle.link)

    # Buat view dengan tombol
    view = discord.ui.View()
    view.add_item(button1)
    view.add_item(button2)

    # Tentukan mention role berdasarkan title
    role_mention = get_role_mention(title)

    channel = bot.get_channel(int(os.getenv('CHANNEL_ID')))
    if channel:
        try:
            await channel.send(content=f"{role_mention} Read Now!", embed=embed, view=view)
        except discord.DiscordException as e:
            logging.error(f"Failed to send message: {e}")
    else:
        logging.error("Channel not found.")
