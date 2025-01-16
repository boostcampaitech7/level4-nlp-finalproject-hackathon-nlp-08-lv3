from flask import Blueprint, jsonify
from db import get_connection as get_main_db_connection

users_bp = Blueprint('users', __name__)

@users_bp.route("/api/users", methods=["GET"])
def get_users():
    conn = get_main_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, name, role FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    users = []
    for r in rows:
        users.append({
            "id": r[0],
            "username": r[1],
            "name": r[2],
            "role": r[3]
        })
    return jsonify({"success": True, "users": users})
