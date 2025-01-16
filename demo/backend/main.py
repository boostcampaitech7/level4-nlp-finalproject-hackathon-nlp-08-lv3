import os
from flask import Flask
from db import init_db as init_main_db, seed_data
from file import init_db as init_file_db

from router.login import login_bp
from router.create_account import create_bp
from router.users import users_bp
from router.questions import questions_bp
from router.feedbacks import feedbacks_bp
from router.upload_files import upload_files_bp

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

init_main_db()
seed_data()
init_file_db()

app.register_blueprint(login_bp)
app.register_blueprint(create_bp)
app.register_blueprint(users_bp)
app.register_blueprint(questions_bp)
app.register_blueprint(feedbacks_bp)
app.register_blueprint(upload_files_bp)

@app.route("/")
def index():
    return "Flask backend - from/to username version"

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(port=5000, debug=True)
