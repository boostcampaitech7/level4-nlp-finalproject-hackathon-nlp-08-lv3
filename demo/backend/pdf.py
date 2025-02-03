from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import matplotlib.font_manager as fm
import sqlite3
import os
from subprocess import run
from llm_sum import summarize_multiple
import requests.exceptions
from book_recommendation import get_book_recommendation, find_lowest_keyword
from send_email import send_report_emails

# 한글 폰트 등록
font_path = "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf"
pdfmetrics.registerFont(TTFont("NanumMyeongjo", font_path))
plt.rcParams['font.family'] = 'NanumMyeongjo'

# DB 경로 설정과 함께 book_chunk 경로도 설정
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")
RESULT_DB_PATH = os.path.join(os.path.dirname(__file__), "db/result.db")
BOOK_CHUNK_DIR = os.path.join(os.path.dirname(__file__), "book_chunk")
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdf")

# 특정 파일이 없을 경우, 특정 파이썬 스크립트를 실행
def run_script_if_file_not_exists(file_name, script_name):
    if not os.path.exists(file_name):
        run(["python", script_name])
    else:
        print(f"파일 '{file_name}'이(가) 이미 존재합니다. 실행하지 않습니다.") # 실행되지 않은 file_name만 출력

def get_user_connection():
    return sqlite3.connect(USER_DB_PATH)

def get_result_connection():
    return sqlite3.connect(RESULT_DB_PATH)

# ==================================  # 1번째 블록
def draw_header(c, data, width, height):
    c.setFont("NanumMyeongjo", 20)
    c.drawString(50, height + 40, data['title'])
    
    c.setFont("NanumMyeongjo", 15)
    c.drawString(50, height, data['name'])
    c.setFont("NanumMyeongjo", 12)
    c.drawString(100, height, data['position'])

# ==================================  # 2번째 블록
def draw_assessment_box(c, data, width, height):
    
    mul_result = summarize_multiple(data['scores'])
    
    styles = getSampleStyleSheet()
    
    box_x, box_y = 50, height
    box_width, box_height = 350, 80

    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.lightgrey)
    c.rect(box_x, box_y, box_width, box_height, fill=1)

    # 텍스트 크기를 동적으로 조정
    text = mul_result
    font_size = 12  # 초기 폰트 크기
    max_font_size = 12
    min_font_size = 6  # 최소 폰트 크기 (너무 작아지지 않도록 제한)

    while font_size >= min_font_size:
        style = ParagraphStyle(
            "CustomStyle",
            parent=styles["Normal"],
            fontName="NanumMyeongjo",
            fontSize=font_size,
            leading=font_size * 1.5  # 줄간격을 글자 크기의 1.5배로 설정
        )
        paragraph = Paragraph(text, style)

        # 텍스트가 박스 크기에 맞는지 확인
        width_needed, height_needed = paragraph.wrap(box_width - 20, box_height - 20)
        
        if height_needed <= box_height - 20:
            break  # 박스에 맞으면 루프 종료
        font_size -= 1  # 텍스트 크기를 줄여서 다시 시도

    # 텍스트 그리기
    paragraph.wrapOn(c, box_width - 20, box_height - 20)
    paragraph.drawOn(c, box_x + 10, box_y + (box_height - height_needed) / 2)  # 중앙 정렬

def draw_grade_box(c, data, width, height):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "NanumMyeongjo"
    style.fontSize = 36
    style.alignment = 1
    paragraph = Paragraph(f"<font color='red'>{data['grade']}</font><br/>", style)
    
    box_x, box_y = 410, height
    box_width, box_height = 80, 80
    
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(box_x, box_y, box_width, box_height, fill=1)
    
    paragraph.wrapOn(c, box_width - 20, box_height - 20)
    paragraph.drawOn(c, box_x + 10, box_y + 50)

# ==================================  # 3번째 블록
def draw_table(c, data, width, height):
    table_data = [
        ["평가항목", "점수 (5점 만점)"],
        *data['scores'],
        ["합계", data['total_score']]
    ]
    
    table = Table(table_data, colWidths=[130, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'NanumMyeongjo'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height)

def draw_radar_chart(c, data, width, height):
    scores = data['scores']
    labels = [score[0] for score in scores]
    values = [float(score[1]) for score in scores]

    team_average = data['team_average']
    team_average_values = [float(score[1]) for score in team_average]

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]  # 점수를 닫기 위해 첫 번째 값을 마지막에 추가
    team_average_values += team_average_values[:1]  # 팀 평균도 동일하게 추가
    angles += angles[:1]  # 각도도 동일하게 추가

    # 레이더 차트 그리기
    fig, ax = plt.subplots(figsize=(4.8, 3), subplot_kw={'polar': True})
    
    # 개인 점수 플롯
    ax.fill(angles, values, color='red', alpha=0.25, label="개인 점수")
    ax.plot(angles, values, color='red', linewidth=2)

    # 팀 평균 점수 플롯
    ax.fill(angles, team_average_values, color='gray', alpha=0.25, label="팀 평균 점수")
    ax.plot(angles, team_average_values, color='gray', linewidth=2)

    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])

    
    font_prop = fm.FontProperties(fname=font_path)
    ax.set_xticklabels(labels, fontsize=8, fontproperties=font_prop)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # 범례 추가
    ax.legend(loc='upper left', bbox_to_anchor=(-0.9, 1.1), fontsize=8, prop=font_prop, frameon=True)

    # 그래프 전체 위치 조정
    fig.subplots_adjust(left=0.2, right=0.9, top=0.9, bottom=0.3)


    # plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=72, facecolor='white')
    plt.close()
    buffer.seek(0)

    c.drawImage(ImageReader(buffer), 320, height-50, width=250, height=180)

def fetch_data():
    user_conn = get_user_connection()
    result_conn = get_result_connection()

    try:
        # 모든 사용자 username 가져오기
        user_cur = user_conn.cursor()
        user_cur.execute("SELECT username FROM users")
        usernames = [row[0] for row in user_cur.fetchall()]

        all_user_data = []

        for username in usernames:
            print(f"\n{'='*50}")
            print(f"사용자 '{username}' 처리 시작")
            print('='*50)
            
            # 사용자 정보 가져오기
            user_cur.execute("""
                SELECT u.name, g.group_name, u.rank 
                FROM users u 
                JOIN groups g ON u.group_id = g.id 
                WHERE u.username = ?
            """, (username,))
            user_info = user_cur.fetchone()
            if not user_info:
                continue

            name = user_info[0]
            position = f"{user_info[1]} {user_info[2]}"

            # 등급 및 총합 점수 가져오기
            result_cur = result_conn.cursor()
            result_cur.execute("SELECT 등급, 총합 FROM multiple WHERE to_username = ?", (username,))
            result_info = result_cur.fetchone()
            if not result_info:
                continue

            grade = result_info[0]
            total_score = result_info[1]

            # 점수 정보 가져오기
            result_cur.execute("PRAGMA table_info(multiple)")
            columns = [col[1] for col in result_cur.fetchall() if col[1] not in ('id', 'to_username', '총합', '등급', 'created_at')]
            scores = []
            for column in columns:
                result_cur.execute(f"SELECT {column} FROM multiple WHERE to_username = ?", (username,))
                score = result_cur.fetchone()
                if score:
                    scores.append([column, score[0]])

            # 수정된 부분: team_average를 먼저 가져온 후 lowest_keyword 찾기
            team_average = []
            for column in columns:
                result_cur.execute(f"SELECT {column} FROM multiple WHERE to_username = 'average'")
                avg_score = result_cur.fetchone()
                if avg_score:
                    team_average.append([column, avg_score[0]])
            
            # 가장 낮은 점수의 키워드 찾기 (team_average 전달)
            lowest_keyword = find_lowest_keyword(scores, team_average)
            print(f"\n[{username}] 가장 낮은 점수의 키워드: {lowest_keyword}")
            
            # book_recommendation.py의 함수 호출
            book_recommendation = get_book_recommendation(username, lowest_keyword)

            all_user_data.append({
                'username': username,
                'name': name,
                'position': position,
                'grade': grade,
                'scores': scores,
                'team_average': team_average,
                'total_score': total_score,
                'book_recommendation': book_recommendation
            })

    finally:
        user_conn.close()
        result_conn.close()
        
    return all_user_data

def draw_team_opinion_and_recommendations(c, data, width, height_st2, table_down):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "NanumMyeongjo"
    style.fontSize = 10
    style.leading = 14
    style.alignment = 0

    x_start = 50
    remaining_width = width - (2 * x_start)
    box_width = remaining_width / 2
    box_padding = 10
    box_y_start = height_st2 - table_down
    bottom_margin = 50
    box_height = box_y_start - bottom_margin
    title_height = 30

    # 첫 번째 박스 - "피드백"
    box_x1 = x_start
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.transparent)
    c.rect(box_x1, bottom_margin, box_width - box_padding / 2, box_height, fill=0)

    c.setFillColor(colors.lightgrey)
    c.rect(box_x1, box_y_start - title_height, box_width - box_padding / 2, title_height, fill=1)

    c.setFont("NanumMyeongjo", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(
        box_x1 + (box_width - box_padding / 2) / 2,
        box_y_start - title_height / 2 - 6,
        "피드백"
    )

    paragraph = Paragraph(data['team_opinion'], style)
    paragraph.wrapOn(c, box_width - box_padding / 2 - 20, box_height - title_height - 10)
    paragraph.drawOn(c, box_x1 + 10, bottom_margin + 10)

    # 두 번째 박스 - "개선 방안"
    box_x2 = box_x1 + box_width + box_padding / 2
    box_width2 = box_width - box_padding / 2
    
    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.transparent)
    c.rect(box_x2, bottom_margin, box_width2, box_height, fill=0)

    # 제목 박스
    c.setFillColor(colors.lightgrey)
    c.rect(box_x2, box_y_start - title_height, box_width2, title_height, fill=1)

    c.setFont("NanumMyeongjo", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(
        box_x2 + box_width2 / 2,
        box_y_start - title_height / 2 - 6,
        "개선 방안"
    )

    # 텍스트 스타일 설정
    title_style = ParagraphStyle(
        'BookTitle',
        fontName='NanumMyeongjo',
        fontSize=12,
        leading=16,
        spaceBefore=0,
        spaceAfter=5
    )
    
    text_style = ParagraphStyle(
        'BookInfo',
        fontName='NanumMyeongjo',
        fontSize=10,
        leading=14,
        spaceBefore=0,
        spaceAfter=5
    )

    # 도서 추천 정보 표시
    book_info = data.get('book_recommendation', {})
    if not book_info:
        return

    # 시작 위치 설정
    content_x = box_x2 + 20
    current_y = box_y_start - title_height - 30  # 제목 아래부터 시작

    # 1. 책 제목
    title = Paragraph(book_info.get('title', ''), title_style)
    title.wrapOn(c, box_width2 - 40, 30)
    title.drawOn(c, content_x, current_y)
    current_y -= 25 # 다음 요소를 위한 간격

    # 2. 저자
    authors = Paragraph(f"저자: {book_info.get('authors', '')}", text_style)
    authors.wrapOn(c, box_width2 - 40, 20)
    authors.drawOn(c, content_x, current_y)
    current_y -= 5  # 다음 요소를 위한 간격

    # 3. 책 이미지
    img_width = 90
    img_height = 120
    
    if book_info.get('thumbnail'):
        try:
            response = requests.get(book_info['thumbnail'])
            if response.status_code == 200:
                img = ImageReader(BytesIO(response.content))
                c.drawImage(img, content_x, current_y - img_height, width=img_width, height=img_height)
        except Exception as e:
            print(f"이미지 로드 실패: {str(e)}")
    current_y -= (img_height + 50)  # 이미지 높이 + 간격

    # 4. 내용 요약
    content_text = book_info.get('contents', '')
    if len(content_text) > 300:  # 내용이 너무 길면 자르기
        content_text = content_text[:300] + "..."
    
    content = Paragraph(f"내용 요약:\n{content_text}", text_style)
    content.wrapOn(c, box_width2 - 40, box_height - (box_y_start - current_y))
    content.drawOn(c, content_x, current_y - 100)  # 내용 요약을 위한 충분한 공간 확보

# ==================================
def generate_pdf(data, filename):
    # pdf 디렉토리가 없으면 생성
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
        
    # pdf 디렉토리 안에 파일 생성
    filepath = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # 높이 기준
    height_st1 = 40
    height_st2 = height_st1 + 440  # 표 시작 위치
    height_st3 = height_st2 + 160
    height_st4 = height_st3 + 100
    table_down = 30  # 표와 상자 사이 간격

    # 데이터에 도서 추천 정보가 없는 경우 기본값 설정
    if 'book_recommendation' not in data:
        data['book_recommendation'] = "도서 추천 정보를 찾을 수 없습니다."
    
    draw_header(c, data, width, height_st4)
    draw_assessment_box(c, data, width, height_st3)
    draw_grade_box(c, data, width, height_st3)
    draw_table(c, data, width, height_st2)
    draw_radar_chart(c, data, width, height_st2)
    draw_team_opinion_and_recommendations(c, data, width, height_st2, table_down)
    
    c.save()
    print(f"PDF 생성 완료: {filename}")
# ===================

if __name__ == "__main__":
    users_data = fetch_data()
    for user_data in users_data:
        user_data.update({
            'title': "인사고과 평가표",
            'team_opinion': "소속 팀 의견",
        })

        filename = f"{user_data['username']}.pdf"
        generate_pdf(user_data, filename)
    
    # PDF 생성이 완료된 후 이메일 전송
    print("\n이메일을 전송 중입니다...")
    send_report_emails()
    print("이메일 전송을 완료했습니다.")
