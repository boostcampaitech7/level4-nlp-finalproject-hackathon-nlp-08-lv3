"""
Routes package initialization.
This package contains all the route blueprints for the application.
"""

from .admin_questions import admin_questions_bp
from .auth import auth_bp
from .feedback import feedback_bp
from .groups import groups_bp
from .mailjet_key import mailjet_key_bp
from .upload_files import upload_files_bp

__all__ = [
    "auth_bp",
    "feedback_bp",
    "groups_bp",
    "upload_files_bp",
    "admin_questions_bp",
    "mailjet_key_bp",
]
