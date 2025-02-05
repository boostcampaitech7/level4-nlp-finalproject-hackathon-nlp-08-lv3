from flask import Blueprint, request, jsonify
from user_db import get_connection

login_bp = Blueprint("login", __name__)

@login_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor()

    # 아이디 존재 여부 확인
    cur.execute("SELECT id, name, role, password FROM users WHERE username=?", (username,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "error": "invalid username"}), 401  # 아이디 오류

    user_id, name, role, correct_password = row

    # 비밀번호 검증
    if password != correct_password:
        conn.close()
        return jsonify({"success": False, "error": "invalid password"}), 401  # 비밀번호 오류

    conn.close()
    return jsonify({"success": True, "user_id": user_id, "name": name, "role": role})
