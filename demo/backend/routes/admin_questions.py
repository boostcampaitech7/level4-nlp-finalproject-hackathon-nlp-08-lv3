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

@admin_questions_bp.route("/api/deadline", methods=["POST"])
def set_deadline():
    data = request.json
    deadline = data.get("deadline")
    remind_days = data.get("remind_days")
    remind_time = data.get("remind_time")
    
    print(f"Received data: deadline={deadline}, remind_days={remind_days}, remind_time={remind_time}")
    
    if not deadline:
        return jsonify({"success": False, "message": "마감일을 입력해주세요."}), 400
        
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 트랜잭션 시작
        conn.execute("BEGIN")
        
        # 기존 마감일 삭제
        cur.execute("DELETE FROM feedback_deadline")
        
        # 새로운 마감일과 리마인드 설정 저장
        print("Executing SQL query with values:", (deadline, remind_days, remind_time))
        cur.execute("""
            INSERT INTO feedback_deadline (deadline, remind_days, remind_time)
            VALUES (?, ?, ?)
        """, (deadline, remind_days, remind_time))
        
        # 트랜잭션 커밋
        conn.commit()
        return jsonify({"success": True, "message": "마감일이 설정되었습니다."})
        
    except Exception as e:
        # 오류 발생시 롤백 및 상세 에러 로깅
        if conn:
            conn.rollback()
        print(f"Error in set_deadline: {str(e)}")
        return jsonify({"success": False, "message": f"설정 중 오류가 발생했습니다: {str(e)}"}), 500
        
    finally:
        if conn:
            conn.close()

@admin_questions_bp.route("/api/deadline", methods=["GET"])
def get_deadline():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT deadline FROM feedback_deadline ORDER BY created_at DESC LIMIT 1")
    result = cur.fetchone()
    
    conn.close()
    
    if result:
        return jsonify({"success": True, "deadline": result[0]})
    return jsonify({"success": True, "deadline": None})