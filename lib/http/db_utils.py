import logging
import pymysql
from datetime import datetime
from lib.config.config import get_db_connection

# Fungsi untuk memformat tanggal
def format_datetime(date_string):
    try:
        dt = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %Z')
    except ValueError:
        logging.error(f"Date format error: {date_string}")
        return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Fungsi untuk mendapatkan last_entry_id dari database
def get_last_entry_id():
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
def set_last_entry_id(entry_id, published, title, link, author):
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
