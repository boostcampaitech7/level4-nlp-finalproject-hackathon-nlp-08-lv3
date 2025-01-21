import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")  # 변경된 부분

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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

    # 5) user_groups
    cur.execute('''
    CREATE TABLE IF NOT EXISTS user_groups (
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, group_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (group_id) REFERENCES groups (id)
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
            (1, 'admin', '관리자', 'admin123', 'admin', '2025-01-14 08:46:08'),
            (2, 'user1', '홍길동', 'user123', 'user', '2025-01-14 08:46:08'),
            (3, 'user2', '이몽룡', 'user123', 'user', '2025-01-14 08:46:08'),
            (4, 'user3', '이춘향', 'user123', 'user', '2025-01-14 08:46:08'),
        ]
        for row in users_data:
            cur.execute("""
                INSERT INTO users (id, username, name, password, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
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

    # 5) user_groups
    cur.execute("SELECT COUNT(*) FROM user_groups")
    user_group_count = cur.fetchone()[0]
    if user_group_count == 0:
        user_groups_data = [
            (2, 1, "2025-01-14 08:46:08"),  # user1 -> Development Team
            (3, 2, "2025-01-14 08:46:08"),  # user2 -> Marketing Team
        ]
        for row in user_groups_data:
            cur.execute("""
                INSERT INTO user_groups (user_id, group_id, assigned_at)
                VALUES (?, ?, ?)
            """, row)

    conn.commit()
    conn.close()
