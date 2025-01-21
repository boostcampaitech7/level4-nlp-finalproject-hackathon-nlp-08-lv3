from flask import Blueprint, request, jsonify
from qa_db import get_connection  # 수정된 부분: feedback_db에서 get_connection 가져오기

user_feedback_write_bp = Blueprint("user_feedback_write", __name__)

@user_feedback_write_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    question_id = data.get("question_id")
    from_username = data.get("from_username")
    to_username = data.get("to_username")
    answer_content = data.get("answer_content", "")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback_results (question_id, from_username, to_username, answer_content)
        VALUES (?, ?, ?, ?)
    """, (question_id, from_username, to_username, answer_content))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "피드백이 제출되었습니다."})
