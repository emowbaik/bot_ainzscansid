import os
import certifi
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env
load_dotenv()

# Ambil konfigurasi dari variabel lingkungan
RSS_URL = os.getenv('RSS_URL')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# Set path sertifikat
os.environ['SSL_CERT_FILE'] = certifi.where()