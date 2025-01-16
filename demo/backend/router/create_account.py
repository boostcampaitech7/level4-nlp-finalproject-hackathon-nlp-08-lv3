from flask import Blueprint, request, jsonify
from db import get_connection as get_main_db_connection

create_bp = Blueprint('create', __name__)

@create_bp.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    name = data.get("name")
    password = data.get("password")
    role = data.get("role")

    conn = get_main_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
    if cur.fetchone()[0] > 0:
        conn.close()
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."}), 400

    cur.execute("""
        INSERT INTO users (username, name, password, role)
        VALUES (?, ?, ?, ?)
    """, (username, name, password, role))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "계정 생성 완료"})
