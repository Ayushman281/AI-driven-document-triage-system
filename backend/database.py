import sqlite3
import os
from config import DATABASE_PATH

def get_db_connection():
    """Create a connection to the SQLite database"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create documents table to store document information
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        format TEXT NOT NULL,
        intent TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source TEXT,
        content TEXT
    )
    ''')
    
    # Create extracted_data table to store fields extracted from documents
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extracted_data (
        document_id TEXT,
        field_name TEXT NOT NULL,
        field_value TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents (id),
        PRIMARY KEY (document_id, field_name)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database when module is imported
init_db()
