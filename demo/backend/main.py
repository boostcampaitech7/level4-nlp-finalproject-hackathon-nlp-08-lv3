from flask import Flask, request, jsonify
from db import init_db, seed_data, get_connection

app = Flask(__name__)

init_db()
seed_data()

@app.route("/")
def index():
    return "Flask backend - from/to username version"

# 1) 로그인
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        user_id, name, role = row
        return jsonify({"success": True, "user_id": user_id, "name": name, "role": role})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

# 2) 계정 생성
@app.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    name = data.get("name")
    password = data.get("password")
    role = data.get("role")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
    if cur.fetchone()[0] > 0:
        conn.close()
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."}), 400

    cur.execute("""
        INSERT INTO users (username, name, password, role)
        VALUES (?, ?, ?, ?)
    """, (username, name, password, role))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "계정 생성 완료"})

# 3) 사용자 목록
@app.route("/api/users", methods=["GET"])
def get_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, name, role FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    users = []
    for r in rows:
        users.append({
            "id": r[0],
            "username": r[1],
            "name": r[2],
            "role": r[3]
        })
    return jsonify({"success": True, "users": users})

# 질문 CRUD
@app.route("/api/questions/<int:question_id>", methods=["PUT"])
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

@app.route("/api/questions/<int:question_id>", methods=["DELETE"])
def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM feedback_questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "질문이 삭제되었습니다."})

@app.route("/api/questions", methods=["GET"])
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

@app.route("/api/questions", methods=["POST"])
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

# 관리자: 특정 사용자(= to_username) 피드백 조회
@app.route("/api/feedback/user", methods=["GET"])
def get_feedback_for_user():
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

# 사용자: 피드백 작성, 내가 받은 피드백 조회
@app.route("/api/feedback", methods=["POST"])
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

@app.route("/api/feedback/my", methods=["GET"])
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

@app.route("/api/questions/<int:question_id>", methods=["GET"])
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
    
if __name__ == "__main__":
    app.run(port=5000, debug=True)
