import logging
import os
import certifi
import requests
from discord.ext import tasks
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Muat variabel lingkungan dari file .env
load_dotenv()

# Ambil konfigurasi dari variabel lingkungan
RSS_URL = os.getenv('RSS_URL')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID'))
GUILD_ID = int(os.getenv('GUILD_ID'))

# Fungsi untuk mendapatkan koneksi database


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=os.getenv('DB_PORT'),
        )
        if connection.is_connected():
            # db_Info = connection.get_server_info()
            # print("Connected to MySQL Server version ", db_Info)
            # cursor = connection.cursor()
            # cursor.execute("select database();")
            # record = cursor.fetchone()
            # print("You're connected to database: ", record)
            return connection

    except Error as e:
        print("Error while connecting to MySQL", e)
        return None

# Set path sertifikat
os.environ['SSL_CERT_FILE'] = certifi.where()

@tasks.loop(minutes=5)
async def respon_code_loop():
    try:
        custom_user_agent = "botAinzScansID/1.0"
        url = RSS_URL
        headers = {
            "User-Agent": custom_user_agent
        }
        response = requests.get(url, headers=headers)

        # Cek status code
        if response.status_code == 200:
            logging.info(
                f"Permintaan berhasil! Status code: {response.status_code}")
            print(f"Response Body: {response.text}")
        elif 500 <= response.status_code < 600:
            logging.warning(
                f"Server mengalami masalah. Status code: {response.status_code}")
        else:
            logging.error(
                f"Terjadi kesalahan. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error saat melakukan permintaan: {e}")


# print(f"Response Body: {response.text}")
# print(headers["User-Agent"])
