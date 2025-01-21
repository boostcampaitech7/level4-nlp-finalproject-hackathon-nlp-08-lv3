from flask import Blueprint, request, jsonify
from qa_db import get_connection

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
    cur.execute("""
        UPDATE feedback_questions
           SET keyword = ?,
               question_text = ?,
               question_type = ?,
               options = ?
         WHERE id = ?
    """, (keyword, question_text, question_type, options, question_id))
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
    cur.execute("SELECT id, keyword, question_text, question_type, options FROM feedback_questions ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    questions = []
    for row in rows:
        questions.append({
            "id": row[0],
            "keyword": row[1],
            "question_text": row[2],
            "question_type": row[3],
            "options": row[4]
        })
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
    cur.execute("""
        INSERT INTO feedback_questions (keyword, question_text, question_type, options)
        VALUES (?, ?, ?, ?)
    """, (keyword, question_text, question_type, options))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "새로운 질문이 등록되었습니다."})

# 질문 단건 조회
@admin_questions_bp.route("/api/questions/<int:question_id>", methods=["GET"])
def get_question_by_id(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, keyword, question_text, question_type, options
          FROM feedback_questions
         WHERE id=?
    """, (question_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        question_data = {
            "id": row[0],
            "keyword": row[1],
            "question_text": row[2],
            "question_type": row[3],
            "options": row[4]
        }
        return jsonify({"success": True, "question": question_data}), 200
    else:
        return jsonify({"success": False, "message": f"Question ID={question_id} not found"}), 404