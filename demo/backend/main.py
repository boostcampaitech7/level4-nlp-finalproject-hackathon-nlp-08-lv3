import os

from flask import Flask

# 현재 파일의 디렉토리를 기준으로 경로 설정
BASE_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(BASE_DIR)

# Blueprint 임포트
from routes import (admin_questions_bp, auth_bp, feedback_bp, groups_bp,
                    mailjet_key_bp, upload_files_bp)

app = Flask(__name__)

# 경로 설정
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_FOLDER = os.path.join(BASE_DIR, "db")
PDF_FOLDER = os.path.join(PARENT_DIR, "pdf")

# 디버그: 경로 출력
print(f"\nDirectory paths:")
print(f"BASE_DIR: {BASE_DIR}")
print(f"DB_FOLDER: {DB_FOLDER}\n")

# Flask 설정
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    DB_FOLDER=DB_FOLDER,
    PDF_FOLDER=PDF_FOLDER,
)

# 필요한 디렉토리 생성
for folder in [UPLOAD_FOLDER, DB_FOLDER, PDF_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# DB 초기화
from db.models.file import init_db as init_file_db
from db.models.qa import init_db, seed_data
from db.models.user import init_users_db, seed_users_data

def init_database():
    init_users_db()
    seed_users_data()
    init_db()
    seed_data()
    init_file_db()

@app.route("/")
def index():
    return "Flask backend - from/to username version"

# 기능별 Blueprint 등록
app.register_blueprint(auth_bp)
app.register_blueprint(feedback_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(mailjet_key_bp)
app.register_blueprint(upload_files_bp)
app.register_blueprint(admin_questions_bp)

if __name__ == "__main__":
    # 데이터베이스 초기화
    init_database()
    # 서버 실행
    app.run(port=5000, debug=True)