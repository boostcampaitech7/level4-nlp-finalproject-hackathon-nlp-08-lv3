import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "feedback.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """
    DB 테이블 구조 (수정 후):
    1) users: (id, username, name, password, role, created_at)
    2) feedback_questions: (id, keyword, question_text, question_type, options, created_at)
    3) feedback_results: (id, question_id, from_username, to_username, answer_content, created_at)
    """
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

    # 2) feedback_questions
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feedback_questions (
        id INTEGER PRIMARY KEY,
        keyword TEXT,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL,
        options TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3) feedback_results
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feedback_results (
        id INTEGER PRIMARY KEY,
        question_id INTEGER NOT NULL,
        from_username TEXT NOT NULL,
        to_username TEXT NOT NULL,
        answer_content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

### 그룹 수정 시작
    # groups 테이블 생성
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
### 그룹 수정 끝

def seed_data():
    """
    최초 실행 시 예시 데이터 (이미 같은 id가 있다면 에러 날 수 있음)
    """
    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------
    # 1) users
    # -----------------------------
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

    # -----------------------------
    # 2) feedback_questions
    # -----------------------------
    cur.execute("SELECT COUNT(*) FROM feedback_questions")
    q_count = cur.fetchone()[0]
    if q_count == 0:
        questions_data = [
            (1, "협업", "팀원과의 협업이 원활했나요?", "single_choice", "매우 그렇다, 그렇다, 아니다", "2025-01-14 08:46:08"),
            (2, "태도", "다른 팀원이 도움이 필요한 경우 적극적으로 협조했나요?", "single_choice", "항상 그렇다, 가끔 그렇다, 거의 없다, 전혀 없다", "2025-01-14 08:46:08"),
        ]
        for row in questions_data:
            cur.execute("""
                INSERT INTO feedback_questions (id, keyword, question_text, question_type, options, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row)

    # -----------------------------
    # 3) feedback_results
    # -----------------------------
    cur.execute("SELECT COUNT(*) FROM feedback_results")
    f_count = cur.fetchone()[0]
    if f_count == 0:
        feedback_data = [
            (1, 1, 'user1', 'user2', '아니다', '2025-01-14 08:46:08'),
        ]
        for row in feedback_data:
            cur.execute("""
                INSERT INTO feedback_results (id, question_id, from_username, to_username, answer_content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row)

### 그룹 수정 시작
    # -----------------------------
    # 4) groups
    # -----------------------------
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

    # -----------------------------
    # 5) user_groups
    # -----------------------------
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
### 그룹 수정 끝

    conn.commit()
    conn.close()
