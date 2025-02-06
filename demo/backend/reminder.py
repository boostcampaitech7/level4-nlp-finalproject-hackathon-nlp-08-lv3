import os
import sqlite3
from datetime import datetime, timedelta
import requests
import time
import schedule
import logging
from mailjet_rest import Client
from collections import defaultdict
import pytz

FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "db/feedback.db")
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")
KST = pytz.timezone('Asia/Seoul')

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
        
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하도록 설정
    return conn

def get_reminder_targets():
    """피드백을 완료하지 않은 사용자들의 이메일과 데드라인 정보를 가져옵니다."""
    conn_feedback = get_db_connection(FEEDBACK_DB_PATH)
    conn_user = get_db_connection(USER_DB_PATH)
    
    try:
        # 현재 활성화된 피드백 데드라인 정보 가져오기 (KST 기준)
        cursor_feedback = conn_feedback.cursor()
        cursor_feedback.execute("""
            SELECT id, deadline, remind_days, remind_time
            FROM feedback_deadline
            WHERE deadline > datetime('now', '+9 hours')
        """)
        deadlines = cursor_feedback.fetchall()
        
        if not deadlines:
            return []

        # 모든 사용자와 그룹 정보를 한 번에 가져오기
        cursor_user = conn_user.cursor()
        cursor_user.execute("""
            SELECT u1.id, u1.username, u1.email, u1.group_id, g.group_name
            FROM users u1
            JOIN groups g ON u1.group_id = g.id
            WHERE EXISTS (
                SELECT 1 FROM users u2 
                WHERE u2.group_id = g.id AND u2.id != u1.id
            )
            AND u1.role = 'user'  -- user 역할을 가진 사용자만 선택
        """)
        users = cursor_user.fetchall()

        # 그룹별 사용자 매핑
        group_members = defaultdict(list)
        for user in users:
            group_members[user['group_id']].append({
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            })

        # 피드백 제출 현황을 한 번에 가져오기
        cursor_feedback.execute("""
            SELECT from_username, to_username 
            FROM feedback_results
        """)
        submitted_feedbacks = set((row[0], row[1]) for row in cursor_feedback.fetchall())

        reminder_targets = []
        for deadline in deadlines:
            for user in users:
                group_id = user['group_id']
                needs_reminder = False
                
                # 같은 그룹의 다른 멤버들에 대한 피드백 제출 여부 확인
                for member in group_members[group_id]:
                    if member['id'] != user['id'] and (user['username'], member['username']) not in submitted_feedbacks:
                        needs_reminder = True
                        break
                
                if needs_reminder:
                    reminder_targets.append({
                        'email': user['email'],
                        'deadline': deadline['deadline'],
                        'remind_days': deadline['remind_days'],
                        'remind_time': deadline['remind_time']
                    })
        
        return reminder_targets
    
    finally:
        conn_feedback.close()
        conn_user.close()

def should_send_reminder(deadline, remind_days, remind_time):
    """현재 시점에 리마인더를 보내야 하는지 확인합니다."""
    now = datetime.now(KST)
    deadline_dt = datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')
    deadline_dt = KST.localize(deadline_dt)
    
    # 시간 비교 (분 단위까지만)
    current_time = now.strftime('%H:%M')
    if current_time != remind_time:
        return False
        
    # 데드라인까지 남은 시간을 시간 단위까지 계산
    time_until_deadline = deadline_dt - now
    days_until_deadline = time_until_deadline.days
    
    # 리마인드 날짜에 해당하는지 확인 (당일 포함)
    return 0 <= days_until_deadline <= remind_days

def send_reminder_emails(targets):
    """여러 대상에게 한 번에 리마인더 이메일을 발송합니다."""
    if not targets:
        return 0
    
    mailjet = get_mailjet_client()
    if not mailjet:
        logging.error("Mailjet credentials not found in database")
        return 0
    
    messages = []
    for target in targets:
        deadline_dt = datetime.strptime(target['deadline'], '%Y-%m-%d %H:%M:%S')
        formatted_deadline = deadline_dt.strftime('%Y년 %m월 %d일')
        
        messages.append({
            'From': {
                'Email': 'beaver.zip@gmail.com',  # Mailjet에서 검증된 발신자 주소 사용
                'Name': 'Feedback Reminder'
            },
            'To': [
                {
                    'Email': target['email'],
                    'Name': target['email'].split('@')[0]
                }
            ],
            'Subject': '[리마인드] 피드백 작성 부탁드립니다.',
            'TextPart': f"""안녕하세요. 아직 피드백을 작성하지 않으셔서 리마인드 메일 드립니다.
피드백 마감일은 {formatted_deadline}입니다.
빠른 작성 부탁드립니다. 감사합니다."""
        })

    try:
        if messages:
            result = mailjet.send.create(data={'Messages': messages})
            if result.status_code == 200:
                return len(messages)
            else:
                logging.error(f"Failed to send emails: {result.json()}")
    except Exception as e:
        logging.error(f"Failed to send emails via Mailjet: {str(e)}")
    
    return 0

def check_and_send_reminders():
    """리마인더를 체크하고 필요한 경우 발송합니다."""
    try:
        start_time = time.time()
        reminder_targets = get_reminder_targets()
        targets_to_send = []
        
        for target in reminder_targets:
            if should_send_reminder(
                target['deadline'],
                target['remind_days'],
                target['remind_time']
            ):
                targets_to_send.append(target)
        
        sent_count = send_reminder_emails(targets_to_send)
        if sent_count > 0:
            logging.info(f"Successfully sent {sent_count} reminder(s)")
        
        end_time = time.time()
        logging.debug(f"Reminder check completed in {end_time - start_time:.2f} seconds")
        
        return f"Successfully sent {sent_count} reminder(s)"
    except Exception as e:
        error_msg = f"Error sending reminders: {str(e)}"
        logging.error(error_msg)
        return error_msg

def setup_logging():
    """로깅 설정을 초기화합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('reminder.log'),
            logging.StreamHandler()
        ]
    )

def run_scheduler():
    """스케줄러를 설정하고 실행합니다."""
    setup_logging()
    logging.info("Starting reminder scheduler...")
    
    # 매 분 시작 시 실행되도록 조정
    def run_on_minute():
        now = datetime.now(KST)
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        wait_seconds = (next_minute - now).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        check_and_send_reminders()
    
    schedule.every().minute.at(":00").do(run_on_minute)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)  # 더 자주 체크하여 정확한 시간에 실행
        except Exception as e:
            logging.error(f"Scheduler error: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
