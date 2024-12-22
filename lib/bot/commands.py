import asyncio
import logging
import discord
import json
from discord.ext import commands
from .utils import send_to_discord
from lib.http.db_utils import fetch_pending_entries, save_pending_entry
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Path to the roles.json file
ROLES_JSON_PATH = 'roles.json'

# Fetch messages function
async def fetch_messages(bot, channel_id, limit=100):
    channel = bot.get_channel(channel_id)
    messages = await channel.history(limit=limit).flatten()
    return messages

# Load roles from roles.json
def load_roles():
    try:
        with open(ROLES_JSON_PATH, 'r', encoding='utf-8') as file:
            roles = json.load(file)
        return roles
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading roles.json: {e}")
        return {"entries": []}

# Save roles to roles.json
def save_roles(roles_data):
    try:
        with open(ROLES_JSON_PATH, 'w', encoding='utf-8') as file:
            json.dump(roles_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving roles.json: {e}")

# Get the next available ID
def get_next_id(roles_data):
    if roles_data['entries']:
        last_id = int(roles_data['entries'][-1]['id'])
        return str(last_id + 1)
    return "1"  # Start with ID 1 if no entries exist

# Add a new entry to roles.json
def add_entry(title, role_id, category):
    roles_data = load_roles()

    new_entry = {
        "id": get_next_id(roles_data),
        "title": title,
        "role": role_id,
        "category": category
    }

    roles_data['entries'].append(new_entry)
    save_roles(roles_data)

    logging.info(f"Entry added: {new_entry}")
    return new_entry

def setup(bot):
    @bot.command(name='list')
    async def list_entries(ctx):
        try:
            messages = await fetch_messages(int(os.getenv('SOURCE_CHANNEL_ID')))
            entries = []

            for message in messages:
                lines = message.content.split('\n')
                if len(lines) >= 4:
                    title = lines[0]
                    link = lines[1]
                    author = lines[2]
                    published = lines[3]
                    entry_id = lines[4]
                    if entry_id not in [e[0] for e in fetch_pending_entries()]:
                        entries.append((title, link, published, author, entry_id))
            
            if not entries:
                await ctx.send("Tidak ada artikel yang ditemukan.")
                return

            entry_list = "\n".join([f"{i+1}. {entry[0]}" for i, entry in enumerate(entries)])
            await ctx.send(f"Daftar artikel:\n{entry_list}\n\nGunakan perintah `!send <nomor>` untuk mengirim artikel yang dipilih.")

        except Exception as e:
            logging.error(f"Error fetching messages: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    @bot.command(name='send')
    async def send_entry(ctx, index: int):
        try:
            messages = await fetch_messages(int(os.getenv('SOURCE_CHANNEL_ID')))
            entries = []

            for message in messages:
                lines = message.content.split('\n')
                if len(lines) >= 4:
                    title = lines[0]
                    link = lines[1]
                    author = lines[2]
                    published = lines[3]
                    entry_id = lines[4]
                    if entry_id not in [e[0] for e in fetch_pending_entries()]:
                        entries.append((title, link, published, author, entry_id))
            
            if index < 1 or index > len(entries):
                await ctx.send("Nomor artikel tidak valid.")
                return

            entry = entries[index - 1]
            title, link, published, author, entry_id = entry

            # Kirim pesan ke Discord
            await send_to_discord(bot, title, link, published, author)
            logging.info(f"Successfully sent notification for: {title}")

            # Simpan entri ke database
            save_pending_entry(entry_id, published, title, link, author)
            await ctx.send(f"Artikel '{title}' telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"Error sending entry: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    @bot.command(name='sendall')
    async def send_all_entries(ctx):
        try:
            messages = await fetch_messages(int(os.getenv('SOURCE_CHANNEL_ID')))
            entries = []

            for message in messages:
                lines = message.content.split('\n')
                if len(lines) >= 4:
                    title = lines[0]
                    link = lines[1]
                    author = lines[2]
                    published = lines[3]
                    entry_id = lines[4]
                    if entry_id not in [e[0] for e in fetch_pending_entries()]:
                        entries.append((title, link, published, author, entry_id))
            
            if not entries:
                await ctx.send("Tidak ada artikel yang ditemukan untuk dikirim.")
                return

            for entry in entries:
                title, link, published, author, entry_id = entry

                await send_to_discord(bot, title, link, published, author)
                logging.info(f"Successfully sent notification for: {title}")

                # Simpan entri ke database
                save_pending_entry(entry_id, published, title, link, author)

            await ctx.send("Semua artikel telah dikirim ke Discord.")
    
        except Exception as e:
            logging.error(f"An error occurred while sending all entries: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    @bot.command(name='addrole')
    # @commands.has_permissions(administrator=True)  # Ensure only admins can use this command
    async def add_role(ctx, title: str, role_id: int, category: str):
        try:
            roles = load_roles()
            if any(entry['role'] == str(role_id) for entry in roles['entries']):
                await ctx.send(f"Peran dengan ID {role_id} sudah ada.")
            else:
                new_entry = add_entry(title, role_id, category)
                await ctx.send(f"Peran '{new_entry['title']}' berhasil ditambahkan dengan ID {new_entry['role']}.")
        except Exception as e:
            logging.error(f"Error adding role: {e}")
            await ctx.send(f"Terjadi kesalahan: {e}")

    @bot.command(name='halo')
    async def halo(ctx):
        intro_message = (
            "Halo! Saya adalah bot yang dirancang untuk membantu mengirimkan notifikasi "
            "artikel terbaru dari RSS feed ke Discord. Anda bisa menggunakan command berikut:\n\n"
            "1. `!list` - Untuk menampilkan daftar artikel terbaru.\n"
            "2. `!send <nomor>` - Untuk mengirim artikel tertentu ke Discord.\n"
            "3. `!sendall` - Untuk mengirim semua artikel terbaru ke Discord.\n\n"
            "Terima kasih telah menggunakan saya! 😊"
        )
        await ctx.send(intro_message)

# def setup_commands(bot):
#     setup(bot)
