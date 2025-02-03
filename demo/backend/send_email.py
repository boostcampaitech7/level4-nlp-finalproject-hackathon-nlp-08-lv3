import os
import sqlite3
import base64
from mailjet_rest import Client
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# 상수 설정
MAILJET_API_KEY = os.getenv('MAILJET_API_KEY')
MAILJET_SECRET_KEY = os.getenv('MAILJET_SECRET_KEY')
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdf")

# Mailjet 클라이언트 초기화
mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')

def get_db_connection():
    """데이터베이스 연결을 생성합니다."""
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_emails():
    """사용자 이메일 정보를 가져옵니다."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, email
            FROM users
            WHERE role = 'user'
        """)
        return {row['username']: row['email'] for row in cursor.fetchall()}
    finally:
        conn.close()

def send_report_emails():
    """생성된 PDF 보고서를 각 사용자의 이메일로 전송합니다."""
    user_emails = get_user_emails()
    
    for username, email in user_emails.items():
        pdf_path = os.path.join(PDF_DIR, f"{username}.pdf")
        
        if not os.path.exists(pdf_path):
            print(f"PDF 파일을 찾을 수 없습니다: {username}")
            continue
            
        with open(pdf_path, 'rb') as pdf_file:
            # PDF 파일을 Base64로 인코딩
            encoded_file = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            data = {
                'Messages': [{
                    'From': {
                        'Email': "beaver.zip@gmail.com",
                        'Name': "피드백 보고서"
                    },
                    'To': [{
                        'Email': email,
                        'Name': username
                    }],
                    'Subject': "피드백 분석 보고서가 도착했습니다",
                    'TextPart': "안녕하세요,\n\n첨부된 파일에서 귀하의 피드백 분석 보고서를 확인하실 수 있습니다.",
                    'HTMLPart': """
                        <p>안녕하세요,</p>
                        <p>첨부된 파일에서 귀하의 피드백 분석 보고서를 확인하실 수 있습니다.</p>
                        <p>감사합니다.</p>
                    """,
                    'Attachments': [{
                        'ContentType': 'application/pdf',
                        'Filename': f"{username}_feedback_report.pdf",
                        'Base64Content': encoded_file
                    }]
                }]
            }
            
            try:
                result = mailjet.send.create(data=data)
                if result.status_code == 200:
                    print(f"이메일 전송 성공: {username} ({email})")
                else:
                    print(f"이메일 전송 실패: {username} ({email}): {result.status_code}")
            except Exception as e:
                print(f"이메일 전송 중 오류 발생: {username} ({email}): {str(e)}")

if __name__ == "__main__":
    send_report_emails()
