import os
from flask import Flask
from qa_db import init_db, seed_data
from file_db import init_db as init_file_db

# Blueprint 임포트
from routes.login import login_bp
from routes.account import account_bp
from routes.admin_questions import admin_questions_bp
from routes.admin_feedback import admin_feedback_bp
from routes.user_feedback_write import user_feedback_write_bp
from routes.user_feedback_result import user_feedback_result_bp
from routes.upload_files import upload_files_bp
from routes.check_feedback import check_feedback_bp
from routes.submit_feedback_bulk import submit_feedback_bulk_bp
from routes.groups import groups_bp  

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FOLDER = 'db'
app.config['DB_FOLDER'] = DB_FOLDER

# DB 초기화 및 시드 데이터 추가
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)
    
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
app.register_blueprint(check_feedback_bp)
app.register_blueprint(submit_feedback_bulk_bp)
app.register_blueprint(groups_bp)


if __name__ == "__main__":
    app.run(port=5000, debug=True)