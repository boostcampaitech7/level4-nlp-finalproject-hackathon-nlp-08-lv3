from flask import Blueprint, send_from_directory
import os

summary_bp = Blueprint('summary', __name__)

@summary_bp.route('/api/summary/<username>')
def summary(username):
    pdf_directory = os.path.join(os.path.dirname(__file__), '../pdf')
    pdf_filename = f'{username}.pdf'
    if os.path.exists(os.path.join(pdf_directory, pdf_filename)):
        return send_from_directory(pdf_directory, pdf_filename)
    else:
        return "PDF file not found", 404
