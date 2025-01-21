import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_users_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1) users
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        group_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups (id)
    )
    ''')

    # 4) groups
    cur.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        group_name TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

def seed_users_data():
    conn = get_connection()
    cur = conn.cursor()

    # 1) users
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    if user_count == 0:
        users_data = [
            (1, 'admin', '관리자', 'admin123', 'admin', None, '2025-01-14 08:46:08'),
            (2, 'user1', 'user1', 'user123', 'user', 1, '2025-01-14 08:46:08'),
            (3, 'user2', 'user2', 'user123', 'user', 2, '2025-01-14 08:46:08'),
            # 나머지 사용자 데이터...
        ]
        for row in users_data:
            cur.execute("""
                INSERT INTO users (id, username, name, password, role, group_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, row)

    # 4) groups
    cur.execute("SELECT COUNT(*) FROM groups")
    group_count = cur.fetchone()[0]
    if group_count == 0:
        groups_data = [
            (1, "Development Team", "2025-01-14 08:46:08"),
            (2, "Marketing Team", "2025-01-14 08:46:08"),
        ]
        for row in groups_data:
            cur.execute("""
                INSERT INTO groups (id, group_name, created_at)
                VALUES (?, ?, ?)
            """, row)

    conn.commit()
    conn.close()