import os
import platform
import sqlite3
import subprocess
import pickle
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from book_recommendation import get_book_recommendation, find_lowest_keyword
from llm_sum import summarize_multiple, summarize_subjective
from send_email import send_report_emails  # send_email.py는 별도 구현(변경 없음)
from common import load_all_book_chunks  # 청크 캐시 로딩 함수

# -------------------------------
# OS별 폰트 경로 및 ReportLab/Matplotlib 설정
if platform.system() == "Linux":
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
else:
    raise RuntimeError("지원되지 않는 OS")

if not os.path.exists(font_path):
    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")

font_prop = fm.FontProperties(fname=font_path)
pdfmetrics.registerFont(TTFont("NanumGothic", font_path))

# -------------------------------
# DB 및 경로 설정
BASE_DIR = os.path.dirname(__file__)
USER_DB_PATH = os.path.join(BASE_DIR, "db/user.db")
RESULT_DB_PATH = os.path.join(BASE_DIR, "db/result.db")
KEYWORD_DB_PATH = os.path.join(BASE_DIR, "db/feedback.db")
PDF_DIR = os.path.join(BASE_DIR, "pdf")

def run_script_if_file_not_exists(file_name, script_name):
    if not os.path.exists(file_name):
        subprocess.run(["python", script_name])
    else:
        pass

def get_user_connection():
    return sqlite3.connect(USER_DB_PATH)

def get_result_connection():
    return sqlite3.connect(RESULT_DB_PATH)

def get_keyword_connection():
    return sqlite3.connect(KEYWORD_DB_PATH)

# -------------------------------
# 재시도 데코레이터 (429 에러 대응)
def retry(exceptions, total_tries=5, initial_wait=1, backoff_factor=2):
    def decorator_retry(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tries = total_tries
            wait = initial_wait
            while tries > 1:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
                        error_info = e.args[0].get('error', {})
                        if error_info.get('code') == 'too_many_requests':
                            time.sleep(wait)
                            tries -= 1
                            wait *= backoff_factor
                            continue
                    raise
            return func(*args, **kwargs)
        return wrapper
    return decorator_retry

# API 호출 시 동시 호출 제한 (최대 4개)
from threading import Semaphore
api_semaphore = Semaphore(4)

@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
def call_get_book_recommendation(username, lowest_keyword):
    with api_semaphore:
        return get_book_recommendation(username, lowest_keyword)

# -------------------------------
# PDF 생성 관련 함수 (draw_***)
def draw_header(c, data, width, height):
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 30)
    c.drawCentredString(width / 2, height - 50, data['title'])

def draw_profile_box(c, data, width, height):
    styles = getSampleStyleSheet()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "profile.png")
    img_width, img_height = 100, 100
    c.drawImage(ImageReader(image_path), 50, height-80, width=img_width, height=img_height)
    c.setFont("NanumGothic", 15)
    c.drawString(180, height + 5, "정보")
    line_x_start, line_x_end = 180, 360
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(line_x_start, height, line_x_end, height)
    c.setFont("NanumGothic", 14)
    info_x, info_y = 180, height - 35
    department, position = data['position'].rsplit(" ", 1) if " " in data['position'] else (data['position'], "")
    info_data = [["이름", data['name']], ["부서", department], ["직급", position]]
    table = Table(info_data, colWidths=[50, 150])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
        ('FONTSIZE', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    table.wrapOn(c, width, height+100)
    table.drawOn(c, info_x, info_y - 40)
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=15,
        alignment=2,
        spaceAfter=5,
    )
    line_x_start2 = width - 280
    title_y = height + 10
    grade_y = title_y - 30
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(line_x_start2 + 70, height, line_x_start2 + 240, height)
    grade_style = ParagraphStyle(
        "GradeStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=50,
        textColor=colors.HexColor("#08c7b4"),
        alignment=2,
    )
    title_paragraph = Paragraph("등급", title_style)
    grade_paragraph = Paragraph(data['grade'], grade_style)
    title_paragraph.wrapOn(c, 100, 30)
    title_paragraph.drawOn(c, line_x_start2, title_y)
    grade_paragraph.wrapOn(c, 100, 30)
    grade_paragraph.drawOn(c, line_x_start2 + 70, grade_y)

def draw_table(c, data, width, height):
    table_data = [
        ["평가항목", "점수 (5점 만점)"],
        *data['scores'],
        ["합계", f"{data['total_score']:.2f}"]
    ]
    table = Table(table_data, colWidths=[130, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#08c7b4")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height-70)

def draw_difference_chart(c, data, width, height):
    prop = fm.FontProperties(fname=font_path, size=14)
    labels = [score[0] for score in data['scores']]
    values = np.array([float(score[1]) for score in data['scores']])
    team_values = np.array([float(score[1]) for score in data['team_average']])
    difference = values - team_values
    best_category = labels[np.argmax(difference)]
    worst_category = labels[np.argmin(difference)]
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    colors_bar = ['#08c7b4' if diff > 0 else 'gray' for diff in difference]
    ax.barh(labels, difference, color=colors_bar, alpha=0.7)
    ax.axvline(0, color='black', linewidth=1)
    for i, (label, v) in enumerate(zip(labels, difference)):
        ha = 'left' if v > 0 else 'right'
        color = '#08c7b4' if label == best_category else "gray" if label == worst_category else "black"
        text = "강점" if label == best_category else "약점" if label == worst_category else ""
        ax.text(v + (0.1 if v > 0 else -0.2), i, text, ha=ha, va='center',
                fontsize=14, fontweight='bold', color=color, fontproperties=prop)
    abs_max = max(abs(difference.min()), abs(difference.max()))
    ax.set_xlim(-abs_max - 0.5, abs_max + 0.5)
    ax.text(0, len(labels), "↓ 평균 이하 | 평균 이상 ↑", fontsize=14, color="black",
            fontweight="bold", ha="center", fontproperties=prop)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontproperties=prop, fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    from io import BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100, facecolor="white", bbox_inches="tight")
    plt.close()
    buffer.seek(0)
    c.drawImage(ImageReader(buffer), width-280, height-90, width=250, height=180)

def draw_assessment_box(c, data, width, height):
    mul_result = summarize_multiple(data['scores'])
    styles = getSampleStyleSheet()
    box_width, box_height = 500, 190
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.lightgrey)
    c.rect(width, height, box_width, box_height, fill=1)
    style = ParagraphStyle(
        "CustomStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=11,
        leading=14
    )
    paragraph = Paragraph(mul_result, style)
    paragraph.wrapOn(c, box_width - 10, box_height - 10)
    paragraph.drawOn(c, width + 5, height + 20)

def draw_team_opinion(c, data, width, height):
    sub_result = summarize_subjective(data['team_opinion'])
    id_to_keyword = {item['id']: item['keyword'] for item in data['feedback_keywords']}
    keyword_to_responses = defaultdict(list)
    for entry in sub_result:
        question_str = entry['question']
        try:
            question_id = int(question_str.split('_')[1])
        except:
            continue
        keyword = id_to_keyword.get(question_id)
        if keyword:
            keyword_to_responses[keyword].append(entry['response'])
    merged_results = [
        {'keyword': keyword, 'response': ' '.join(responses)}
        for keyword, responses in keyword_to_responses.items()
    ]
    styles = getSampleStyleSheet()
    box_x, box_y = 50, height
    box_width, box_height = width-100, 390
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(box_x, box_y, box_width, box_height, fill=1)
    text = ""
    for response_dict in merged_results:
        text += f"<b>{response_dict['keyword']}</b><br/>"
        text += response_dict['response'] + "<br/><br/>"
    font_size = 12
    while font_size >= 9:
        style = ParagraphStyle(
            "CustomStyle",
            parent=styles["Normal"],
            fontName="NanumGothic",
            fontSize=font_size,
            leading=font_size * 1.5
        )
        paragraph = Paragraph(text, style)
        width_needed, height_needed = paragraph.wrap(box_width - 20, box_height - 20)
        if height_needed <= box_height - 20:
            break
        font_size -= 1
    paragraph.wrapOn(c, box_width - 20, box_height - 20)
    paragraph.drawOn(c, box_x + 10, box_y + (box_height - height_needed) / 2)

def draw_book_recommendations(c, data, width, height_st2, table_down):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "NanumGothic"
    style.fontSize = 10
    style.leading = 14
    style.alignment = 0
    x_start = 50
    remaining_width = width - (2 * x_start)
    box_width = remaining_width
    box_padding = 10
    box_y_start = height_st2 - table_down
    bottom_margin = 100
    box_height = box_y_start - bottom_margin
    title_height = 30
    box_x2 = x_start
    box_width2 = box_width - box_padding / 2
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.transparent)
    c.rect(box_x2, bottom_margin, box_width2, box_height, fill=0)
    c.setFillColor(colors.HexColor("#08c7b4"))
    c.rect(box_x2, box_y_start - title_height, box_width2, title_height, fill=1)
    c.setFont("NanumGothic", 12)
    c.setFillColor(colors.white)
    c.drawCentredString(
        box_x2 + box_width2 / 2,
        box_y_start - title_height / 2 - 6,
        "피드백을 기반으로 AI가 도서 3개를 추천해드립니다"
    )
    content_x = box_x2 + 20
    current_y = box_y_start - title_height - 50
    for i, book_info in enumerate(data.get('book_recommendation', [])[:3]):
        if i > 0:
            c.setStrokeColor(colors.grey)
            c.line(box_x2 + 10, current_y + 10, box_x2 + box_width2 - 10, current_y + 10)
            current_y -= 30
        title_text = f"{book_info.get('title', '')}"
        title_par = Paragraph(title_text, styles["Normal"])
        title_par.wrapOn(c, box_width2 - 40, 30)
        title_par.drawOn(c, content_x, current_y)
        current_y -= 25
        authors = Paragraph(f"저자: {book_info.get('authors', '')}", styles["Normal"])
        authors.wrapOn(c, box_width2 - 40, 20)
        authors.drawOn(c, content_x, current_y)
        current_y -= 15
        img_width = 60
        img_height = 80
        image_y = current_y - img_height
        if book_info.get('thumbnail'):
            try:
                response = requests.get(book_info['thumbnail'])
                if response.status_code == 200:
                    from io import BytesIO
                    img = ImageReader(BytesIO(response.content))
                    c.drawImage(img, content_x, image_y, width=img_width, height=img_height)
            except Exception as e:
                pass
        content_text = book_info.get('contents', '')
        summary_x = content_x + img_width + 20
        summary_width = box_width2 - img_width - 60
        content_par = Paragraph(f"내용 요약:\n{content_text}", styles["Normal"])
        content_par.wrapOn(c, summary_width, img_height)
        content_par.drawOn(c, summary_x, image_y + img_height - styles["Normal"].leading - 65)
        current_y = image_y - 40
        if current_y < bottom_margin + 50:
            break

def generate_pdf(data, filename):
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
    filepath = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    background_color = colors.white
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    # 첫번째 페이지
    draw_header(c, data, width, height - 50)
    draw_profile_box(c, data, width, height - 180)
    height_st = height - 350
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 20)
    c.drawCentredString(90, height_st + 10, '종합 평가')
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height_st, width - 50, height_st)
    draw_table(c, data, width, height_st - 100)
    draw_difference_chart(c, data, width, height_st - 100)
    draw_assessment_box(c, data, 50, 80)
    # 두번째 페이지
    c.showPage()
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    draw_team_opinion(c, data, width, 50)
    # 세번째 페이지
    c.showPage()
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 20)
    c.drawString(50, height-70, '추천 도서')
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height-80, width - 50, height-80)
    draw_book_recommendations(c, data, width, height-100, 10)
    c.save()

# -------------------------------
# 데이터베이스 최적화 적용한 사용자 데이터 가져오기
def fetch_data():
    from collections import defaultdict
    user_conn = get_user_connection()
    result_conn = get_result_connection()
    keyword_conn = get_keyword_connection()
    try:
        user_cur = user_conn.cursor()
        user_cur.execute("SELECT username, name, group_id, rank FROM users WHERE role = 'user'")
        users = user_cur.fetchall()
        # 그룹 정보를 한 번에 조회
        user_cur.execute("SELECT id, group_name FROM groups")
        groups = {row[0]: row[1] for row in user_cur.fetchall()}
        
        result_cur = result_conn.cursor()
        result_cur.execute("PRAGMA table_info(multiple)")
        all_columns = [col[1] for col in result_cur.fetchall()]
        mul_columns = [col for col in all_columns if col not in ('id', 'to_username', '총합', '등급', 'created_at')]
        result_cur.execute("SELECT * FROM multiple WHERE to_username = 'average'")
        avg_row = result_cur.fetchone()
        team_average = []
        if avg_row:
            col_idx = {col: idx for idx, col in enumerate(all_columns)}
            for col in mul_columns:
                team_average.append([col, avg_row[col_idx[col]]])
        
        # 사용자별 multiple 데이터를 한 번에 조회
        usernames = [u[0] for u in users]
        if usernames:
            placeholders = ','.join('?' for _ in usernames)
            query = f"SELECT * FROM multiple WHERE to_username IN ({placeholders})"
            result_cur.execute(query, usernames)
            multiple_rows = result_cur.fetchall()
        else:
            multiple_rows = []
        multiple_by_user = {}
        if multiple_rows:
            col_idx = {col: idx for idx, col in enumerate(all_columns)}
            for row in multiple_rows:
                uname = row[col_idx['to_username']]
                multiple_by_user[uname] = row
        
        # 사용자별 주관식 피드백을 한 번에 조회
        if usernames:
            placeholders = ','.join('?' for _ in usernames)
            query = f"SELECT * FROM subjective WHERE to_username IN ({placeholders})"
            result_cur.execute(query, usernames)
            subjective_rows = result_cur.fetchall()
        else:
            subjective_rows = []
        subjective_by_user = defaultdict(list)
        if subjective_rows:
            subj_desc = [d[0] for d in result_cur.description]
            for row in subjective_rows:
                data = dict(zip(subj_desc, row))
                subjective_by_user[data.get('to_username')].append(data)
        
        # 피드백 키워드는 한 번만 조회
        keyword_cur = keyword_conn.cursor()
        keyword_cur.execute("SELECT id, keyword FROM feedback_questions")
        feedback_keywords = [{"id": r[0], "keyword": r[1]} for r in keyword_cur.fetchall()]
        
        all_user_data = []
        if multiple_rows:
            col_idx = {col: idx for idx, col in enumerate(all_columns)}
        for user in users:
            username, name, group_id, rank = user
            group_name = groups.get(group_id, "")
            position = f"{group_name} {rank}"
            row = multiple_by_user.get(username)
            if not row:
                continue
            grade = row[col_idx.get("등급")]
            total_score = row[col_idx.get("총합")]
            scores = []
            for col in mul_columns:
                scores.append([col, row[col_idx.get(col)]])
            lowest_keyword = find_lowest_keyword(scores, team_average)
            subj_list = subjective_by_user.get(username, [])
            team_opinion = []
            for data in subj_list:
                for key, value in data.items():
                    if key not in ('id', 'to_username', 'created_at') and value is not None:
                        team_opinion.append([key, value])
            all_user_data.append({
                'username': username,
                'name': name,
                'position': position,
                'grade': grade,
                'scores': scores,
                'team_average': team_average,
                'total_score': total_score,
                'team_opinion': team_opinion,
                'feedback_keywords': feedback_keywords,
                'lowest_keyword': lowest_keyword,
                'title': "인사고과 평가표"
            })
    finally:
        user_conn.close()
        result_conn.close()
        keyword_conn.close()
    return all_user_data

# -------------------------------
# 개별 사용자의 데이터를 받아 도서 추천 API 호출 및 PDF 생성
def process_user(user_data):
    username = user_data['username']
    lowest_keyword = user_data.get('lowest_keyword')
    if not lowest_keyword:
        user_data['book_recommendation'] = None
    else:
        recommendation = call_get_book_recommendation(username, lowest_keyword)
        user_data['book_recommendation'] = recommendation
    filename = f"{username}.pdf"
    generate_pdf(user_data, filename)
    print(f"[{username}] 보고서 생성 완료")
    return username

if __name__ == "__main__":
    # 청크 파일을 미리 메모리에 로드 (개선사항 2)
    load_all_book_chunks()
    users_data = fetch_data()
    # CPU 수에 따라 최대 워커 수 조정 (개선사항 5)
    max_workers = min(os.cpu_count() or 4, 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_user, user_data) for user_data in users_data]
        for future in as_completed(futures):
            try:
                _ = future.result()
            except Exception as e:
                print(f"Error processing user: {e}")
    send_report_emails()
