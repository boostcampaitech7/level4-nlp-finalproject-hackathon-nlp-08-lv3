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
    cur.execute("SELECT id, name, role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        user_id, name, role = row
        return jsonify({"success": True, "user_id": user_id, "name": name, "role": role})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
