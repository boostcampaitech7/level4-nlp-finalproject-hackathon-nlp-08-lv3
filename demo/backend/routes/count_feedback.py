from flask import Blueprint, jsonify
from qa_db import get_connection  # DB 연결 함수

feedback_count_bp = Blueprint("feedback_count", __name__)

# 특정 사용자가 고유하게 피드백을 작성한 개수
@feedback_count_bp.route("/api/feedback/count/written/<username>", methods=["GET"])
def count_written_feedback(username):
    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT COUNT(DISTINCT to_username) FROM feedback_results
    WHERE from_username=?
    """
    cur.execute(query, (username,))
    written_count = cur.fetchone()[0]
    conn.close()

    return jsonify({"success": True, "count": written_count})

# 특정 사용자가 고유하게 받은 피드백 개수
@feedback_count_bp.route("/api/feedback/count/received/<username>", methods=["GET"])
def count_received_feedback(username):
    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT COUNT(DISTINCT from_username) FROM feedback_results
    WHERE to_username=?
    """
    cur.execute(query, (username,))
    received_count = cur.fetchone()[0]
    conn.close()

    return jsonify({"success": True, "count": received_count})
