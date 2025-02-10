import os
import sqlite3

from .user import init_users_db, seed_users_data

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "feedback.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    DB 테이블 구조:
    1) users: (id, username, name, password, role, email, created_at)
    2) feedback_questions: (id, keyword, question_text, question_type, options, created_at)
    3) feedback_results: (id, question_id, from_username, to_username, answer_content, created_at)
    4) feedback_deadline: (id, start_date, deadline, remind_days, remind_time, created_at)
    """
    conn = get_connection()
    cur = conn.cursor()

    # feedback_questions
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS feedback_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL,
        options TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # feedback_results
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS feedback_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        from_username TEXT NOT NULL,
        to_username TEXT NOT NULL,
        answer_content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # feedback_deadline
    cur.execute(
        """
    DROP TABLE IF EXISTS feedback_deadline;
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS feedback_deadline (
        id INTEGER PRIMARY KEY,
        start_date DATETIME NOT NULL,
        deadline DATETIME NOT NULL,
        remind_days INTEGER NOT NULL,
        remind_time TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    )

    conn.commit()
    conn.close()

    init_users_db()


def seed_data():
    """
    최초 실행 시 데이터 초기화
    """
    conn = get_connection()
    cur = conn.cursor()

    # feedback_questions와 feedback_results는 빈 상태로 시작
    conn.commit()
    conn.close()

    seed_users_data()
