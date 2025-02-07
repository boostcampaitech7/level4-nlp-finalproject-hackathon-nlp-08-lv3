"""
Feedback related routes.
This module contains all feedback-related endpoints including admin and user feedback functionalities.
"""

from db.models.qa import get_connection
from db.models.user import UserDB
from flask import Blueprint, jsonify, request

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/api/feedback/user", methods=["GET"])
def admin_feedback():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "사용자 이름이 필요합니다."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT fr.*, fq.question_text 
            FROM feedback_results fr
            JOIN feedback_questions fq ON fr.question_id = fq.id
            WHERE fr.to_username = ?
        """,
            (username,),
        )
        feedbacks = [
            {
                "id": row[0],
                "question_id": row[1],
                "from_username": row[2],
                "to_username": row[3],
                "answer_content": row[4],
                "created_at": row[5],
                "question_text": row[6],
            }
            for row in cur.fetchall()
        ]
        return jsonify({"success": True, "feedbacks": feedbacks})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/feedback/check", methods=["GET"])
def check_feedback():
    from_username = request.args.get("from_username")
    to_username = request.args.get("to_username")

    if not from_username or not to_username:
        return (
            jsonify({"success": False, "message": "Missing username parameters"}),
            400,
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        # feedback_results 테이블에서 피드백 제출 여부 확인
        cur.execute(
            """
            SELECT COUNT(*) FROM feedback_results 
            WHERE from_username = ? AND to_username = ?
        """,
            (from_username, to_username),
        )
        count = cur.fetchone()[0]
        return jsonify({"success": True, "already_submitted": count > 0})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/feedback/count/written/<username>", methods=["GET"])
def count_written_feedback(username):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT to_username) 
            FROM feedback_results 
            WHERE from_username = ?
        """,
            (username,),
        )
        count = cur.fetchone()[0]
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/feedback/count/received/<username>", methods=["GET"])
def count_received_feedback(username):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT COUNT(DISTINCT from_username) 
            FROM feedback_results 
            WHERE to_username = ?
        """,
            (username,),
        )
        count = cur.fetchone()[0]
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/admin/feedback/status", methods=["GET"])
def get_admin_feedback_status():
    conn = get_connection()
    user_conn = UserDB.get_connection()

    try:
        # 전체 사용자 수 조회
        user_cur = user_conn.cursor()
        user_cur.execute('SELECT COUNT(*) FROM users WHERE role != "admin"')
        total_users = user_cur.fetchone()[0]

        # 피드백을 1개 이상 작성한 사용자 수 조회
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(DISTINCT from_username) 
            FROM feedback_results
        """
        )
        users_with_feedback = cur.fetchone()[0]

        # 피드백 완료율 계산
        completion_rate = (
            (users_with_feedback / total_users * 100) if total_users > 0 else 0
        )

        # 전체 피드백 수 조회
        cur.execute("SELECT COUNT(*) FROM feedback_results")
        total_feedbacks = cur.fetchone()[0]

        return jsonify(
            {
                "success": True,
                "total_users": total_users,
                "users_with_feedback": users_with_feedback,
                "completion_rate": round(completion_rate, 1),
                "total_feedbacks": total_feedbacks,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()
        user_conn.close()


@feedback_bp.route("/api/feedback/bulk", methods=["POST"])
def submit_feedback_bulk():
    feedbacks = (
        request.json
        if isinstance(request.json, list)
        else request.json.get("feedbacks", [])
    )

    conn = get_connection()
    cur = conn.cursor()

    try:
        for feedback in feedbacks:
            cur.execute(
                """
                INSERT INTO feedback_results 
                (question_id, from_username, to_username, answer_content, created_at) 
                VALUES (?, ?, ?, ?, datetime('now'))
            """,
                (
                    feedback["question_id"],
                    feedback["from_username"],
                    feedback["to_username"],
                    feedback["answer_content"],
                ),
            )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/feedback/my", methods=["GET"])
def user_feedback_result():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "사용자 이름이 필요합니다."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT fr.*, fq.question_text 
            FROM feedback_results fr
            JOIN feedback_questions fq ON fr.question_id = fq.id
            WHERE fr.to_username = ?
        """,
            (username,),
        )
        feedbacks = [
            {
                "id": row[0],
                "question_id": row[1],
                "from_username": row[2],
                "to_username": row[3],
                "answer_content": row[4],
                "created_at": row[5],
                "question_text": row[6],
            }
            for row in cur.fetchall()
        ]
        return jsonify({"success": True, "feedbacks": feedbacks})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@feedback_bp.route("/api/feedback", methods=["POST"])
def user_feedback_write():
    data = request.json
    question_id = data.get("question_id")
    from_username = data.get("from_username")
    to_username = data.get("to_username")
    answer_content = data.get("answer_content")

    if not all([question_id, from_username, to_username, answer_content]):
        return jsonify({"success": False, "message": "모든 필드를 입력해주세요."}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO feedback_results 
            (question_id, from_username, to_username, answer_content, created_at) 
            VALUES (?, ?, ?, ?, datetime('now'))
        """,
            (question_id, from_username, to_username, answer_content),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
