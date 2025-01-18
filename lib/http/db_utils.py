import logging
import pymysql
# from datetime import datetime
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                judul_name VARCHAR(255) NOT NULL,
                chapter VARCHAR(255) NOT NULL,
                tipe_komik VARCHAR(255) NOT NULL,
                posisi_name VARCHAR(255) NOT NULL,
                reporter_id BIGINT NOT NULL,
                reporter_name VARCHAR(255) NOT NULL,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        except pymysql.MySQLError as e:
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
        except pymysql.MySQLError as e:
            logging.error(f"Failed to save processed entry {entry_id} to database: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

# Fungsi untuk mendapatkan last_entry_id dari database
def get_last_entry_id() -> int:
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT entry_id FROM entries ORDER BY published DESC LIMIT 1')
            result = cursor.fetchone()
            logging.info(f"Fetched last_entry_id: {result[0] if result else 'None'}")
            return result[0] if result else None
        except pymysql.MySQLError as e:
            logging.error(f"Failed to fetch last_entry_id: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")
    return None

# Fungsi untuk menyimpan entry_id, published, title, link, dan author ke database
def set_last_entry_id(entry_id: int, published: str, title: str, link: str, author: str):
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
                logging.info(f"Set entry_id {entry_id} with published date {formatted_published}, title {title}, link {link}, and author {author}")
        except pymysql.MySQLError as e:
            logging.error(f"Failed to save entry_id {entry_id} to database: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

# Fungsi untuk menyimpan entri yang tertunda ke database
def save_pending_entry(entry_id: int, published: str, title: str, link: str, author: str):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            formatted_published = format_datetime(published)
            if formatted_published:
                cursor.execute(
                    '''
                    INSERT INTO pending_entries (entry_id, published, title, link, author) 
                    VALUES (%s, %s, %s, %s, %s) 
                    ON DUPLICATE KEY UPDATE published=%s, title=%s, link=%s, author=%s
                    ''',
                    (entry_id, formatted_published, title, link, author, formatted_published, title, link, author)
                )
                conn.commit()
                logging.info(f"Saved pending entry {entry_id}")
        except pymysql.MySQLError as e:
            logging.error(f"Failed to save pending entry {entry_id}: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")

# Fungsi untuk mengambil entri yang tertunda dari database
def fetch_pending_entries() -> list:
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT entry_id, published, title, link, author FROM pending_entries')
            entries = cursor.fetchall()
            logging.info(f"Fetched {len(entries)} pending entries")
            return entries
        except pymysql.MySQLError as e:
            logging.error(f"Failed to fetch pending entries: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")
    return []

# Fungsi untuk menghapus entri yang telah dikirim dari database
def delete_pending_entry(entry_id: int):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pending_entries WHERE entry_id = %s', (entry_id,))
            conn.commit()
            logging.info(f"Deleted pending entry {entry_id}")
        except pymysql.MySQLError as e:
            logging.error(f"Failed to delete pending entry {entry_id}: {e}")
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
        except pymysql.MySQLError as e:
            logging.error(f"Failed to delete old entries: {e}")
        finally:
            conn.close()
    else:
        logging.error("No database connection available")


def save_project_report(
    judul_name, chapter, tipe_komik, posisi_name, reporter_id, reporter_name
):
    """Simpan laporan proyek ke database."""
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO project_reports (
                judul_name, chapter, tipe_komik, posisi_name, reporter_id, reporter_name
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            judul_name, chapter, tipe_komik, posisi_name, reporter_id, reporter_name
        ))
        connection.commit()
    connection.close()
    
def get_reports_for_month(month: int):
    """
    Ambil laporan proyek dari database berdasarkan bulan.
    :param month: Bulan (1-12).
    :return: List laporan proyek.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, judul_name, chapter, tipe_komik, posisi_name, reporter_name, reported_at
            FROM project_reports
            WHERE MONTH(reported_at) = %s AND YEAR(reported_at) = YEAR(CURRENT_DATE())
        """
        cursor.execute(query, (month,))
        reports = cursor.fetchall()
        conn.close()
        return reports
    except Exception as e:
        print(f"Error fetching reports: {e}")
        return []