from flask import Blueprint, request, jsonify
from user_db import get_connection
import sqlite3

account_bp = Blueprint("account", __name__)

# 아이디 중복 확인 
@account_bp.route("/api/check_username", methods=["GET"])
def check_username():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "아이디를 입력하세요."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cur.fetchone()
        available = existing_user is None  # 아이디가 없으면 True, 있으면 False

        return jsonify({"available": available})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# 이메일 중복 확인 
@account_bp.route("/api/check_email", methods=["GET"])
def check_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"success": False, "message": "이메일을 입력하세요."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_email = cur.fetchone()
        available = existing_email is None  # 이메일이 없으면 True, 있으면 False

        return jsonify({"available": available})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# 기존 계정 생성 
@account_bp.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    name = data.get("name")
    password = data.get("password")
    role = data.get("role")
    email = data.get("email")
    group_id = data.get("group_id")
    rank = data.get("rank")

    if not all([username, name, password, role, email]):
        return jsonify({"success": False, "message": "모든 필수 항목을 입력해주세요."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, name, password, role, email, group_id, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, name, password, role, email, group_id, rank))
        conn.commit()
        return jsonify({"success": True, "message": "계정이 생성되었습니다."})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "계정 생성 중 오류가 발생했습니다."}), 400
    finally:
        conn.close()

# 사용자 목록 조회
@account_bp.route("/api/users", methods=["GET"])
def get_users():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT u.id, u.username, u.name, u.role, u.email, u.group_id, g.group_name, u.rank
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
                "email": r[4],
                "group_id": r[5],
                "group_name": r[6],
                "rank": r[7]
            })
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()