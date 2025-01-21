import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "db/file_uploads.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 파일 업로드 테이블 생성
    cur.execute('''
    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

def save_file_metadata(filename, file_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO uploaded_files (filename, file_path)
        VALUES (?, ?)
    """, (filename, file_path))
    conn.commit()
    conn.close()
