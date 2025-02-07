import atexit
import os
import shutil

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
DEFAULT_DATA_FOLDER = os.path.join(BASE_DIR, "default_data")

# 디버그: 경로 출력
print(f"\nDirectory paths:")
print(f"BASE_DIR: {BASE_DIR}")
print(f"DB_FOLDER: {DB_FOLDER}")
print(f"DEFAULT_DATA_FOLDER: {DEFAULT_DATA_FOLDER}\n")

# Flask 설정
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    DB_FOLDER=DB_FOLDER,
    PDF_FOLDER=PDF_FOLDER,
    DEFAULT_DATA_FOLDER=DEFAULT_DATA_FOLDER,
)

# 필요한 디렉토리 생성
for folder in [UPLOAD_FOLDER, DB_FOLDER, PDF_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

# default_data에서 .db 파일 복사
print(f"Checking if default_data exists at: {DEFAULT_DATA_FOLDER}")
if os.path.exists(DEFAULT_DATA_FOLDER):
    print(f"Found default_data directory")
    db_files = [f for f in os.listdir(DEFAULT_DATA_FOLDER) if f.endswith(".db")]
    print(f"Found {len(db_files)} .db files: {db_files}")

    for db_file in db_files:
        src = os.path.join(DEFAULT_DATA_FOLDER, db_file)
        dst = os.path.join(DB_FOLDER, db_file)
        print(f"Copying {src} to {dst}")
        try:
            shutil.copy2(src, dst)
            print(f"Successfully copied {db_file}")
        except Exception as e:
            print(f"Error copying {db_file}: {str(e)}")
else:
    print(f"default_data directory not found!")

from db.models.file import init_db as init_file_db
from db.models.qa import init_db, seed_data
# DB 초기화
from db.models.user import init_users_db, seed_users_data


def init_database():
    init_users_db()
    seed_users_data()
    init_db()
    seed_data()
    init_file_db()


def cleanup():
    pdf_folder = app.config["PDF_FOLDER"]  # 이미 절대 경로
    db_folder = app.config["DB_FOLDER"]
    result_db_path = os.path.join(db_folder, "result.db")
    feedback_db_path = os.path.join(db_folder, "feedback.db")
    user_db_path = os.path.join(db_folder, "user.db")

    if os.path.exists(result_db_path):
        os.remove(result_db_path)
        os.remove(feedback_db_path)
        os.remove(user_db_path)
    if os.path.exists(pdf_folder):
        for file in os.listdir(pdf_folder):
            file_path = os.path.join(pdf_folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)


atexit.register(cleanup)


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
    # 필요한 디렉토리 생성
    for folder in [UPLOAD_FOLDER, DB_FOLDER, PDF_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # default_data에서 .db 파일 복사
    if os.path.exists(DEFAULT_DATA_FOLDER):
        for db_file in os.listdir(DEFAULT_DATA_FOLDER):
            if db_file.endswith(".db"):
                shutil.copy(os.path.join(DEFAULT_DATA_FOLDER, db_file), DB_FOLDER)

    # 데이터베이스 초기화
    init_database()
    # 서버 실행
    app.run(port=5000, debug=True)
