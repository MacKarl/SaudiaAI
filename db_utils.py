import sqlite3
import json

def get_db_connection():
    """Establish a new database connection."""
    conn = sqlite3.connect('database.db', check_same_thread=False)
    return conn

def create_table():
    """Create the database table if it doesn't exist."""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                json_instance TEXT
            )
        ''')
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def save_thread(thread_id, json_instance={'test': 'test'}):
    """Save a thread to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO threads (thread_id, json_instance)
        VALUES (?, ?)
    ''', (thread_id, json.dumps(json_instance)))
    conn.commit()
    conn.close()


