import os
import sqlite3

from db.models.user import get_connection, init_mailjet_table
from flask import Blueprint, jsonify, request

mailjet_key_bp = Blueprint("mailjet_key", __name__)

USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")


@mailjet_key_bp.route("/api/mailjet-key", methods=["POST"])
def set_mailjet_keys():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "JSON 데이터가 필요합니다."}), 400

    api_key = data.get("API_KEY")
    secret_key = data.get("SECRET_KEY")
    if not api_key or not secret_key:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "API_KEY와 SECRET_KEY 모두 제공되어야 합니다.",
                }
            ),
            400,
        )

    init_mailjet_table()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM mailjet_keys")
        conn.execute(
            "INSERT INTO mailjet_keys (api_key, secret_key) VALUES (?, ?)",
            (api_key, secret_key),
        )
        conn.commit()
        return jsonify(
            {"success": True, "message": "Mailjet 키가 성공적으로 저장되었습니다."}
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"데이터베이스 오류: {str(e)}"}),
            500,
        )
    finally:
        conn.close()


@mailjet_key_bp.route("/api/mailjet-key", methods=["GET"])
def get_mailjet_keys():
    init_mailjet_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT api_key, secret_key FROM mailjet_keys ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not row:
            return jsonify({"success": False, "message": "No Mailjet key is set."}), 404

        return jsonify(
            {
                "success": True,
                "API_KEY": row["api_key"],
                "SECRET_KEY": row["secret_key"],
            }
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"데이터베이스 오류: {str(e)}"}),
            500,
        )
    finally:
        conn.close()
