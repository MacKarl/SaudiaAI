import sqlite3
import json

def get_db_connection():
    """Establish a new database connection."""
    conn = sqlite3.connect('database.db')
    return conn

def create_table():
    """Create the database table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            json_instance TEXT
        )
    ''')
    conn.commit()
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

def query_thread(thread_id):
    """Retrieve a thread from the database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT json_instance FROM threads WHERE thread_id = ?
    ''', (thread_id,))
    result = cursor.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None
