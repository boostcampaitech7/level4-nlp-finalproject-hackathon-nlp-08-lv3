from flask import Blueprint, request, jsonify
from db import get_connection

submit_feedback_bulk_bp = Blueprint("submit_feedback_bulk", __name__)

@submit_feedback_bulk_bp.route("/api/feedback/bulk", methods=["POST"])
def submit_feedback_bulk():
    data = request.json

    if not isinstance(data, list) or not data:
        return jsonify({"success": False, "message": "유효한 데이터가 필요합니다."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        for feedback in data:
            question_id = feedback.get("question_id")
            from_username = feedback.get("from_username")
            to_username = feedback.get("to_username")
            answer_content = feedback.get("answer_content")

            if not (question_id and from_username and to_username and answer_content):
                raise ValueError("모든 필드가 채워져야 합니다.")

            cur.execute("""
                INSERT INTO feedback_results (question_id, from_username, to_username, answer_content)
                VALUES (?, ?, ?, ?)
            """, (question_id, from_username, to_username, answer_content))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"success": True, "message": "모든 피드백이 성공적으로 저장되었습니다."})