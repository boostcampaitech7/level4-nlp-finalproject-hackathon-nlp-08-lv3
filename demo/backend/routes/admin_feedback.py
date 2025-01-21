from flask import Blueprint, request, jsonify
from qa_db import get_connection

admin_feedback_bp = Blueprint("admin_feedback", __name__)

@admin_feedback_bp.route("/api/feedback/user", methods=["GET"])
def get_feedback_for_user():
    to_username = request.args.get("username")
    if not to_username:
        return jsonify({"success": False, "message": "username is required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT id, question_id, from_username, to_username, answer_content, created_at
      FROM feedback_results
     WHERE to_username=?
     ORDER BY created_at DESC
    """
    cur.execute(query, (to_username,))
    rows = cur.fetchall()
    conn.close()

    feedbacks = []
    for r in rows:
        fb_id, q_id, f_uname, t_uname, ans, created = r
        feedbacks.append({
            "feedback_id": fb_id,
            "question_id": q_id,
            "from_username": f_uname,
            "to_username": t_uname,
            "answer_content": ans,
            "created_at": created
        })
    return jsonify({"success": True, "feedbacks": feedbacks})
