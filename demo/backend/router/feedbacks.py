from flask import Blueprint, request, jsonify
from db import get_connection as get_main_db_connection

feedbacks_bp = Blueprint('feedbacks', __name__)

@feedbacks_bp.route("/api/feedback/user", methods=["GET"])
def get_feedback_for_user():
    to_username = request.args.get("username")
    if not to_username:
        return jsonify({"success": False, "message": "username is required"}), 400

    conn = get_main_db_connection()
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

@feedbacks_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    question_id = data.get("question_id")
    from_username = data.get("from_username")
    to_username = data.get("to_username")
    answer_content = data.get("answer_content", "")

    conn = get_main_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback_results (question_id, from_username, to_username, answer_content)
        VALUES (?, ?, ?, ?)
    """, (question_id, from_username, to_username, answer_content))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "피드백이 제출되었습니다."})

@feedbacks_bp.route("/api/feedback/my", methods=["GET"])
def get_my_feedback():
    to_username = request.args.get("username")
    if not to_username:
        return jsonify({"success": False, "message": "username is required"}), 400

    conn = get_main_db_connection()
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
