import logging
import mysql.connector
from mysql.connector import Error
from lib.config.config import get_db_connection
from dateutil import parser

# Fungsi untuk memformat tanggal
def format_datetime(date_string: str) -> str:
    try:
        dt = parser.parse(date_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        logging.error(f"Date format error: {date_string} - {e}")
        return None

def setup_database():
    """Setup tabel di database jika belum ada."""
    connection = get_db_connection()
    with connection.cursor() as cursor:
        #tabel role_blacklist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_blacklist (
                role_id BIGINT PRIMARY KEY,
                role_name VARCHAR(255) NOT NULL,
                added_at DATETIME NOT NULL
            )
        """)
        connection.commit()
    connection.close()

def entry_already_processed(entry_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT entry_id FROM entries WHERE entry_id = %s', (entry_id,))
            result = cursor.fetchone()
            return result is not None
        except Error.MySQLError as e:
            logging.error(f"Failed to check if entry_id {entry_id} is already processed: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")
    return False

def save_processed_entry(entry_id, published, title, link, author):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            formatted_published = format_datetime(published)
            if formatted_published:
                cursor.execute(
                    '''
                    INSERT INTO entries (entry_id, published, title, link, author)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE published=%s, title=%s, link=%s, author=%s
                    ''',
                    (entry_id, formatted_published, title, link, author, formatted_published, title, link, author)
                )
                conn.commit()
        except Error.MySQLError as e:
            logging.error(f"Failed to save processed entry {entry_id} to database: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

def delete_old():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()

            # Hapus entri yang lebih dari 3 hari dari pending_entries
            cursor.execute('''
                DELETE FROM pending_entries
                WHERE published < NOW() - INTERVAL 3 DAY
            ''')
            logging.info("Deleted old entries from pending_entries")

            # Hapus entri yang lebih dari 3 hari dari entries
            cursor.execute('''
                DELETE FROM entries
                WHERE published < NOW() - INTERVAL 3 DAY
            ''')
            logging.info("Deleted old entries from entries")

            # Reset tabel project_reports setiap 2 bulan
            cursor.execute('''
                DELETE FROM project_reports
                WHERE reported_at < NOW() - INTERVAL 2 MONTH
            ''')
            logging.info("Deleted old entries from project_reports")

            conn.commit()
        except Error.MySQLError as e:
            logging.error(f"Failed to delete old entries: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

# Fungsi untuk menambahkan role ke dalam daftar blacklist
def add_role_to_blacklist(role_id, role_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO role_blacklist (role_id, role_name, added_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE role_name = %s, added_at = NOW()
        """
        cursor.execute(query, (role_id, role_name, role_name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Failed to add role to blacklist: {e}")
        return False

# Fungsi untuk menghapus role dari blacklist
def remove_role_from_blacklist(role_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "DELETE FROM role_blacklist WHERE role_id = %s"
        cursor.execute(query, (role_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Failed to remove role from blacklist: {e}")
        return False

# Fungsi untuk mengecek apakah role ada dalam daftar blacklist
def is_role_blacklisted(role_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT 1 FROM role_blacklist WHERE role_id = %s LIMIT 1"
        cursor.execute(query, (role_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logging.error(f"Failed to check if role is blacklisted: {e}")
        return False