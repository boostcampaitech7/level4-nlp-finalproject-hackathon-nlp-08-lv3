import os
import sqlite3
import base64
import re
from concurrent import futures
from mailjet_rest import Client
from openai import OpenAI
import logging
from dotenv import load_dotenv

load_dotenv()
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdf")

# 이메일 발신자 설정
SENDER_NAME = "인사팀"

# Solar API 설정
solar_client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# Mailjet 클라이언트 초기화
def get_mailjet_client():
    """데이터베이스에서 Mailjet 키를 조회하여 클라이언트 생성"""
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT api_key, secret_key FROM mailjet_keys ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            return Client(auth=(row['api_key'], row['secret_key']), version='v3.1')
        return None
    finally:
        conn.close()

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
        # 필요한 컬럼만 명시적으로 선택
        cursor.execute("""
            SELECT username, name, email
            FROM users
            WHERE role = 'user'
        """)
        return {row['username']: {'email': row['email'], 'name': row['name']} for row in cursor.fetchall()}
    finally:
        conn.close()

def get_admin_emails():
    """관리자 이메일 정보를 가져옵니다."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT email
            FROM users
            WHERE role = 'admin'
        """)
        return [row['email'] for row in cursor.fetchall()]
    finally:
        conn.close()

def generate_email_content():
    """Chat API를 사용하여 이메일의 제목과 내용을 생성합니다.
    
    Returns:
        tuple: (제목 템플릿, 본문 템플릿)
        
    Raises:
        Exception: API 호출 실패 시 발생
    """
    prompt = """
아래 조건에 맞춰, 친근하고 유머러스한 말투로 이메일 제목과 본문을 작성해줘. 이메일은 각 팀원에게 동료들이 평가한 '피드백 보고서' 파일을 첨부하여 전달하는 내용이야.
{name}은 실제 이름이 들어갈 자리를 표시하는 placeholder야.

[조건]
1. 수신자: {name}
2. 발신자: 인사팀

3. 이메일 제목:
   - 제목은 반드시 "[이메일 제목]"이라는 라벨 바로 다음 줄에 작성할 것.
   - 작성 예시를 참고해 밝고 유쾌한 말투로 작성할 것.

4. 이메일 본문:
   - 본문은 반드시 "[이메일 본문]"이라는 라벨 바로 다음 줄부터 시작할 것.
   - 첫 줄에 "안녕하세요, {name}님!"으로 인사말을 작성할 것.
   - 첨부 파일(피드백 보고서)이 포함되었음을 명시할 것.
   - 자세한 피드백은 웹페이지에서 확인할 수 있음을 명시할 것.
   - 전체 내용을 여러 문단으로 구분하여, 각 문단 사이에 한 줄 이상의 빈 줄을 추가해 가독성을 높일 것.
   - 이모티콘과 이모지를 적절히 사용하되, 최대 3개만 사용할 것.
   - 작성 예시를 참고해 대화체의 친근한 말투와 자연스러운 유머를 섞어 작성할 것.

5. 작성 예시:
[이메일 제목]
{name}님, 피드백 보고서 도착했어요! 💌

[이메일 본문]
안녕하세요, {name}님!!
오늘도 좋은 하루 보내고 계신가요?

첨부된 파일은 팀원들이 보내주신 피드백 보고서입니다!
제 피드백을 살짝 읽어봤는데, 평소에 몰랐던 저의 장점과 아쉬운 점들이 쏟아져 나오더라고요 🥺
팀원들이 정성스럽게 작성해준 피드백을 보면서, 한 걸음 더 성장할 수 있을 것 같아 기쁘더라구요! 😼

더 자세한 피드백은 웹페이지에서 확인하실 수 있습니다!!
혹시 피드백에 대해 궁금한 점이나 더 이야기 나누고 싶으신 부분이 있다면 언제든 편하게 연락주세요~!!
그럼 오늘도 화이팅하시고, 즐거운 하루 보내세요~! ◜◡◝
"""

    try:
        response = solar_client.chat.completions.create(
            model="solar-pro",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=False
        )
        
        content = response.choices[0].message.content
    except Exception as e:
        print(f"이메일 템플릿 생성 중 오류 발생: {str(e)}")
        raise
    
    # 정규표현식을 사용하여 [이메일 제목]과 [이메일 본문] 라벨 이후의 내용을 추출합니다.
    title_match = re.search(r"(?m)^\[이메일 제목\]\s*\n(.+)", content)
    body_match = re.search(r"(?m)^\[이메일 본문\]\s*\n([\s\S]+)", content)
    
    if title_match:
        subject = title_match.group(1).strip()
    else:
        subject = "피드백 보고서가 도착했어요! 💌"
    
    if body_match:
        body = body_match.group(1).strip()
    else:
        body = content
    
    return subject, body

def send_admin_notification(success_count):
    """관리자에게 보고서 전송 완료 알림을 보냅니다."""
    admin_emails = get_admin_emails()
    mailjet = get_mailjet_client()
    if not mailjet:
        logging.error("Mailjet credentials not found in database")
        return 0      
     
    if not admin_emails:
        print("관리자 이메일을 찾을 수 없습니다.")
        return
        
    data = {
        'Messages': [{
            'From': {
                'Email': admin_emails[0],
                'Name': SENDER_NAME
            },
            'To': [{'Email': email, 'Name': "관리자"} for email in admin_emails],
            'Subject': "보고서 전달 완료",
            'TextPart': f"보고서 전달이 완료됐습니다.\n총 {success_count}명의 사용자에게 보고서가 전송되었습니다."
        }]
    }
    
    try:
        result = mailjet.send.create(data=data)
        if result.status_code == 200:
            print("관리자 알림 전송 성공")
        else:
            print(f"관리자 알림 전송 실패: {result.status_code}")
    except Exception as e:
        print(f"관리자 알림 전송 중 오류 발생: {str(e)}")

def send_single_email(args):
    """단일 사용자에게 이메일을 전송합니다."""
    username, user_info, subject_template, body_template = args
    pdf_path = os.path.join(PDF_DIR, f"{username}.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"PDF 파일을 찾을 수 없습니다: {username}")
        return 0
    admin_email = get_admin_emails()
    mailjet = get_mailjet_client()
    
    if not mailjet:
        logging.error("Mailjet credentials not found in database")
        return 0    
    
    with open(pdf_path, 'rb') as pdf_file:
        encoded_file = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        # 템플릿의 {name} 부분을 실제 사용자 이름으로 대체
        subject = subject_template.format(name=user_info['name'])
        text_content = body_template.format(name=user_info['name'])
        
        data = {
            'Messages': [{
                'From': {
                    'Email': admin_email[0],
                    'Name': SENDER_NAME
                },
                'To': [{
                    'Email': user_info['email'],
                    'Name': username
                }],
                'Subject': subject,
                'TextPart': text_content,
                'Attachments': [{
                    'ContentType': 'application/pdf',
                    'Filename': f"피드백 보고서_{user_info['name']}.pdf",
                    'Base64Content': encoded_file
                }]
            }]
        }
        
        try:
            result = mailjet.send.create(data=data)
            if result.status_code == 200:
                print(f"이메일 전송 성공: {username} ({user_info['email']})")
                return 1
            else:
                print(f"이메일 전송 실패: {username} ({user_info['email']}): {result.status_code}")
                return 0
        except Exception as e:
            print(f"이메일 전송 중 오류 발생: {username} ({user_info['email']}): {str(e)}")
            return 0

def send_report_emails():
    """생성된 PDF 보고서를 각 사용자의 이메일로 병렬로 전송합니다."""
    user_emails = get_user_emails()
    subject_template, body_template = generate_email_content()
    
    # 이메일 발송을 위한 인자 리스트 생성
    email_args = [
        (username, user_info, subject_template, body_template)
        for username, user_info in user_emails.items()
    ]
    
    # ThreadPoolExecutor를 사용하여 병렬로 이메일 전송
    with futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send_single_email, email_args))
    
    success_count = sum(results)
    
    # 모든 이메일 전송이 완료된 후 관리자에게 알림 전송
    send_admin_notification(success_count)

if __name__ == "__main__":
    send_report_emails()