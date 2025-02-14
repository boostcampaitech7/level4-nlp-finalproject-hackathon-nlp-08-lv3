"""
Authentication related routes.
This module contains all authentication-related endpoints including login and account management.
"""

import sqlite3

from db.models.user import UserDB
from flask import Blueprint, jsonify, request

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = UserDB.get_connection()
    cur = conn.cursor()

    # 아이디 존재 여부 확인
    cur.execute(
        "SELECT id, name, role, password FROM users WHERE username=?", (username,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "error": "invalid username"}), 401

    user_id, name, role, correct_password = row

    # 비밀번호 검증
    if password != correct_password:
        conn.close()
        return jsonify({"success": False, "error": "invalid password"}), 401

    conn.close()
    return jsonify({"success": True, "user_id": user_id, "name": name, "role": role})


@auth_bp.route("/api/check_username", methods=["GET"])
def check_username():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "아이디를 입력하세요."}), 400

    conn = UserDB.get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cur.fetchone()
        available = existing_user is None

        return jsonify({"available": available})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/api/check_email", methods=["GET"])
def check_email():
    email = request.args.get("email")
    if not email:
        return jsonify({"success": False, "message": "이메일을 입력하세요."}), 400

    conn = UserDB.get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_email = cur.fetchone()
        available = existing_email is None

        return jsonify({"available": available})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    name = data.get("name")
    email = data.get("email")
    role = data.get("role", "user")
    group_id = data.get("group_id")
    rank = data.get("rank")

    conn = UserDB.get_connection()
    cur = conn.cursor()

    try:
        # 사용자 생성
        cur.execute(
            "INSERT INTO users (username, password, name, email, role, group_id, rank) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, password, name, email, role, group_id, rank),
        )
        conn.commit()
        return jsonify(
            {"success": True, "message": "계정이 성공적으로 생성되었습니다."}
        )
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "이미 존재하는 계정입니다."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@auth_bp.route("/api/users", methods=["GET"])
def get_users():
    conn = UserDB.get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT u.id, u.username, u.name, u.email, u.role, u.group_id, u.rank, g.group_name
            FROM users u
            LEFT JOIN groups g ON u.group_id = g.id
        """
        )
        users = []
        for row in cur.fetchall():
            user = {
                "id": row[0],
                "username": row[1],
                "name": row[2],
                "email": row[3],
                "role": row[4],
                "group_id": row[5],
                "rank": row[6],
                "group_name": row[7],
            }
            users.append(user)
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
