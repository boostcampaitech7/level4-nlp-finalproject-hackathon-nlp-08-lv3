import os
import re
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from file_db import save_file_metadata

upload_files_bp = Blueprint('upload_files', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpeg', 'png', 'bmp', 'tiff', 'heic', 'docx', 'xlsx', 'pptx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def custom_secure_filename(filename):
    # 한글과 ASCII 문자만 남기고 나머지는 `_`로 대체
    filename = re.sub(r'[^\w가-힣.-]', '_', filename)
    # 보안을 위해 파일 이름이 너무 길 경우 잘라냄 (예: 255자 제한)
    return filename[:255]

@upload_files_bp.route("/api/upload_file", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # 수정된 secure_filename 적용
        filename = custom_secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        try:
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            file.save(file_path)
            save_file_metadata(filename, file_path)
            return jsonify({"success": True, "message": "파일이 성공적으로 업로드되었습니다."}), 200
        except Exception as e:
            return jsonify({"success": False, "message": f"파일 저장 중 오류가 발생했습니다: {e}"}), 500
    else:
        return jsonify({"success": False, "message": "허용되지 않는 파일 형식입니다."}), 400
