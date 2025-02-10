import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user.db")


class UserDB:
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_PATH)


def get_connection():
    return UserDB.get_connection()


def init_users_db():
    conn = get_connection()
    cur = conn.cursor()

    # users
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT NOT NULL,
        group_id INTEGER,
        rank TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups (id)
    )
    """
    )

    # groups
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    conn.commit()
    conn.close()


def seed_users_data():
    """
    데이터베이스 초기화 함수
    """
    conn = get_connection()
    cur = conn.cursor()

    # users와 groups 테이블은 빈 상태로 시작
    conn.commit()
    conn.close()


def init_mailjet_table():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mailjet_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            secret_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()
