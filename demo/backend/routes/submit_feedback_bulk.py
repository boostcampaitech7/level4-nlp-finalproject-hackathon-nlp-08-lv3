from flask import Blueprint, request, jsonify
from qa_db import get_connection  # 수정된 부분: feedback_db에서 get_connection 가져오기
import datetime
from datetime import datetime

submit_feedback_bulk_bp = Blueprint("submit_feedback_bulk", __name__)

@submit_feedback_bulk_bp.route("/api/feedback/bulk", methods=["POST"])
def submit_feedback_bulk():
    # 마감일 체크
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT deadline FROM feedback_deadline ORDER BY created_at DESC LIMIT 1")
    deadline_result = cur.fetchone()
    
    if deadline_result:
        deadline = datetime.strptime(deadline_result[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > deadline:
            return jsonify({
                "success": False, 
                "message": "피드백 제출 기한이 마감되었습니다."
            }), 400
    
    data = request.json

    if not isinstance(data, list) or not data:
        return jsonify({"success": False, "message": "유효한 데이터가 필요합니다."}), 400

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