from flask import Blueprint, request, jsonify
from qa_db import get_connection  # 수정된 부분: feedback_db에서 get_connection 가져오기

user_feedback_result_bp = Blueprint("user_feedback_result", __name__)

@user_feedback_result_bp.route("/api/feedback/my", methods=["GET"])
def get_my_feedback():
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
        fb_id, q_id, from_u, to_u, ans, created = r
        feedbacks.append({
            "feedback_id": fb_id,
            "question_id": q_id,
            "from_username": from_u,
            "to_username": to_u,
            "answer_content": ans,
            "created_at": created
        })
    return jsonify({"success": True, "feedbacks": feedbacks})
