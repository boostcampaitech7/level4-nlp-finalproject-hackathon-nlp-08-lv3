import os
from flask import Flask
from db import init_db, seed_data
from file import init_db as init_file_db

# Blueprint 임포트
from routes.login import login_bp
from routes.account import account_bp
from routes.admin_questions import admin_questions_bp
from routes.admin_feedback import admin_feedback_bp
from routes.user_feedback_write import user_feedback_write_bp
from routes.user_feedback_result import user_feedback_result_bp
from routes.upload_files import upload_files_bp

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# DB 초기화
init_db()
seed_data()
init_file_db()

@app.route("/")
def index():
    return "Flask backend - from/to username version"

# 기능별 Blueprint 등록
app.register_blueprint(login_bp)
app.register_blueprint(account_bp)
app.register_blueprint(admin_questions_bp)
app.register_blueprint(admin_feedback_bp)
app.register_blueprint(user_feedback_write_bp)
app.register_blueprint(user_feedback_result_bp)
app.register_blueprint(upload_files_bp)

# 피드백 작성 중복 확인
@app.route("/api/feedback/check", methods=["GET"])
def check_feedback():
    from_username = request.args.get("from_username")
    to_username = request.args.get("to_username")
    
    if not from_username or not to_username:
        return jsonify({"success": False, "message": "from_username and to_username are required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT COUNT(*) FROM feedback_results
     WHERE from_username=? AND to_username=?
    """
    cur.execute(query, (from_username, to_username))
    feedback_count = cur.fetchone()[0]
    conn.close()

    if feedback_count > 0:
        return jsonify({"success": True, "already_submitted": True})
    else:
        return jsonify({"success": True, "already_submitted": False})
        

@app.route("/api/feedback/bulk", methods=["POST"])
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

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(port=5000, debug=True)