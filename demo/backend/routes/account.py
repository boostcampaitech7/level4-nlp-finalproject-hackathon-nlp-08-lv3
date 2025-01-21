from flask import Blueprint, request, jsonify
from user_db import get_connection

account_bp = Blueprint("account", __name__)

# 계정 생성
@account_bp.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    name = data.get("name")
    password = data.get("password")
    role = data.get("role")
    group_id = data.get("group_id")
    rank = data.get("rank")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
    if cur.fetchone()[0] > 0:
        conn.close()
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."}), 400

    cur.execute("""
        INSERT INTO users (username, name, password, role, group_id, rank)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, name, password, role, group_id, rank))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "계정 생성 완료"})

# 사용자 목록 조회
@account_bp.route("/api/users", methods=["GET"])
def get_users():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT u.id, u.username, u.name, u.role, u.group_id, g.group_name, u.rank
            FROM users u
            LEFT JOIN groups g ON u.group_id = g.id
            ORDER BY u.id ASC
        """)
        rows = cur.fetchall()
        
        users = []
        for r in rows:
            users.append({
                "id": r[0],
                "username": r[1],
                "name": r[2],
                "role": r[3],
                "group_id": r[4],
                "group_name": r[5],
                "rank": r[6]
            })
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()