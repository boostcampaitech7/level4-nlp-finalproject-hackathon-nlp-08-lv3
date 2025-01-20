from flask import Blueprint, request, jsonify
from db import get_connection

check_feedback_bp = Blueprint("check_feedback", __name__)

@check_feedback_bp.route("/api/feedback/check", methods=["GET"])
def check_feedback():
    from_username = request.args.get("from_username")
    to_username = request.args.get("to_username")
    
    if not from_username or not to_username:
        return jsonify({"success": False, "message": "from_username and to_username are required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT COUNT(*) FROM feedback_results
     WHERE from_username=? AND to_username=?
    """
    cur.execute(query, (from_username, to_username))
    feedback_count = cur.fetchone()[0]
    conn.close()

    if feedback_count > 0:
        return jsonify({"success": True, "already_submitted": True})
    else:
        return jsonify({"success": True, "already_submitted": False})