import datetime

from db.models.qa import get_connection
from flask import Blueprint, jsonify, request

admin_questions_bp = Blueprint("admin_questions", __name__)


# 질문 수정
@admin_questions_bp.route("/api/questions/<int:question_id>", methods=["PUT"])
def update_question(question_id):
    data = request.json
    keyword = data.get("keyword")
    question_text = data.get("question_text")
    question_type = data.get("question_type")
    options = data.get("options")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE feedback_questions
           SET keyword = ?,
               question_text = ?,
               question_type = ?,
               options = ?
         WHERE id = ?
    """,
        (keyword, question_text, question_type, options, question_id),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "질문이 수정되었습니다."})


# 질문 삭제
@admin_questions_bp.route("/api/questions/<int:question_id>", methods=["DELETE"])
def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM feedback_questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "질문이 삭제되었습니다."})


# 질문 목록 조회
@admin_questions_bp.route("/api/questions", methods=["GET"])
def get_questions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, keyword, question_text, question_type, options FROM feedback_questions ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()

    questions = []
    for row in rows:
        questions.append(
            {
                "id": row[0],
                "keyword": row[1],
                "question_text": row[2],
                "question_type": row[3],
                "options": row[4],
            }
        )
    return jsonify({"success": True, "questions": questions})


# 질문 생성
@admin_questions_bp.route("/api/questions", methods=["POST"])
def create_question():
    data = request.json
    keyword = data.get("keyword")
    question_text = data.get("question_text")
    question_type = data.get("question_type")
    options = data.get("options")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO feedback_questions (keyword, question_text, question_type, options)
        VALUES (?, ?, ?, ?)
    """,
        (keyword, question_text, question_type, options),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "새로운 질문이 등록되었습니다."})


# 질문 단건 조회
@admin_questions_bp.route("/api/questions/<int:question_id>", methods=["GET"])
def get_question_by_id(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, keyword, question_text, question_type, options
          FROM feedback_questions
         WHERE id=?
    """,
        (question_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        question_data = {
            "id": row[0],
            "keyword": row[1],
            "question_text": row[2],
            "question_type": row[3],
            "options": row[4],
        }
        return jsonify({"success": True, "question": question_data}), 200
    else:
        return (
            jsonify(
                {"success": False, "message": f"Question ID={question_id} not found"}
            ),
            404,
        )


@admin_questions_bp.route("/api/deadline", methods=["POST"])
def set_deadline():
    data = request.json
    deadline = data.get("deadline")
    start_date = data.get("start_date")
    remind_days = data.get("remind_days")
    remind_time = data.get("remind_time")

    if not all([deadline, start_date, remind_days is not None, remind_time]):
        return (
            jsonify({"success": False, "message": "필수 입력값이 누락되었습니다."}),
            400,
        )

    try:
        start_date_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        deadline_dt = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.datetime.now()

        if start_date_dt <= current_dt:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "시작 기한은 현재 시점 이후로 설정해주세요.",
                    }
                ),
                400,
            )

        if deadline_dt <= start_date_dt:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "마감 기한은 시작 기한 이후로 설정해주세요.",
                    }
                ),
                400,
            )

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM feedback_deadline")
        cur.execute(
            """
            INSERT INTO feedback_deadline (start_date, deadline, remind_days, remind_time)
            VALUES (?, ?, ?, ?)
        """,
            (start_date, deadline, remind_days, remind_time),
        )
        conn.commit()

        return jsonify({"success": True, "message": "마감일 설정이 완료되었습니다."})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_questions_bp.route("/api/deadline", methods=["GET"])
def get_deadline():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT start_date, deadline FROM feedback_deadline ORDER BY created_at DESC LIMIT 1"
    )
    result = cur.fetchone()

    if result:
        return jsonify(
            {"success": True, "start_date": result[0], "deadline": result[1]}
        )
    else:
        return jsonify({"success": True, "start_date": None, "deadline": None})
