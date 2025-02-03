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
from llm_sum import summarize_multiple, summarize_subjective
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

# ==================================  '인사평가표 제목', 이름 , 직급 => 완료
def draw_header(c, data, width, height):
    c.setFont("NanumMyeongjo", 20)
    c.drawString(50, height + 40, data['title'])
    
    c.setFont("NanumMyeongjo", 15)
    c.drawString(50, height, data['name'])
    c.setFont("NanumMyeongjo", 12)
    c.drawString(100, height, data['position'])

# ==================================  # 한줄평가, 등급
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

# ==================================  # 표, 막대그래프 => 완료
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
    
def draw_difference_chart(c, data, width, height):

    prop = fm.FontProperties(fname=font_path, size=14)

    # 데이터 준비
    labels = [score[0] for score in data['scores']]
    values = np.array([float(score[1]) for score in data['scores']])
    team_values = np.array([float(score[1]) for score in data['team_average']])

    # 팀 평균 대비 차이 계산
    difference = values - team_values

    # 가장 잘한 항목과 가장 부족한 항목 찾기
    best_category = labels[np.argmax(difference)]
    worst_category = labels[np.argmin(difference)]

    # 그래프 크기 조정
    fig, ax = plt.subplots(figsize=(6, 4))

    # 색상 설정 (잘한 것은 초록색, 부족한 것은 빨간색 강조)
    colors = ['darkgreen' if label == best_category else 'darkred' if label == worst_category else 'green' if diff > 0 else 'red' for label, diff in zip(labels, difference)]
    
    ax.barh(labels, difference, color=colors, alpha=0.7)
    ax.axvline(0, color='black', linewidth=1)  # 중앙선 추가

    # **텍스트 라벨 추가 (강점/약점 강조)**
    for i, (label, v) in enumerate(zip(labels, difference)):
        ha = 'left' if v > 0 else 'right'
        color = "green" if label == best_category else "red" if label == worst_category else "black"
        text = "강점" if label == best_category else "약점" if label == worst_category else ""
        # ax.text(v, i, f"{v:.1f}", ha=ha, va='center', fontsize=12, fontweight='bold', color='black', fontproperties=prop)  # 숫자
        ax.text(v + (0.1 if v > 0 else -0.2), i, text, ha=ha, va='center', fontsize=14, fontweight='bold', color=color, fontproperties=prop)  # 강점/약점

    # X축 범위 자동 조정
    abs_max = max(abs(difference.min()), abs(difference.max()))
    ax.set_xlim(-abs_max - 0.5, abs_max + 0.5)

    # **그래프 상단에 "평균보다 낮음/높음" 표시 (더 크게 & 중앙 정렬)**
    ax.text(0, len(labels), "내 점수가 평균보다 낮음    |    내 점수가 평균보다 높음", fontsize=14, color="black", fontweight="bold", ha="center", fontproperties=prop)

    # **Y축 레이블 유지**
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontproperties=prop, fontsize=12)

    # 그리드 스타일 조정
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    # 그래프 저장 및 PDF 삽입
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100, facecolor="white", bbox_inches="tight")
    plt.close()
    buffer.seek(0)

    # PDF에 이미지 추가
    c.drawImage(ImageReader(buffer), width-50-250-10, height-30, width=250, height=180)

# ==================================  # 사용자 정보 가져오기
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
            mul_columns = [col[1] for col in result_cur.fetchall() if col[1] not in ('id', 'to_username', '총합', '등급', 'created_at')]
            scores = []
            for column in mul_columns:
                result_cur.execute(f"SELECT {column} FROM multiple WHERE to_username = ?", (username,))
                score = result_cur.fetchone()
                if score:
                    scores.append([column, score[0]])

            # team_average를 먼저 가져온 후 lowest_keyword 찾기
            team_average = []
            for column in mul_columns:
                result_cur.execute(f"SELECT {column} FROM multiple WHERE to_username = 'average'")
                avg_score = result_cur.fetchone()
                if avg_score:
                    team_average.append([column, avg_score[0]])
            
            # 가장 낮은 점수의 키워드 찾기 (team_average 전달)
            lowest_keyword = find_lowest_keyword(scores, team_average)
            print(f"\n[{username}] 가장 낮은 점수의 키워드: {lowest_keyword}")
            
            # 주관식 문항 가져오기
            result_cur.execute("PRAGMA table_info(subjective)")
            sub_rows = [row[1] for row in result_cur.fetchall() if row[1] not in ('id', 'to_username', 'created_at')]
            team_opinion = []
            for row in sub_rows:
                result_cur.execute(f"SELECT {row} FROM subjective WHERE to_username = ?", (username,))
                opinion = result_cur.fetchall()  # 모든 결과를 가져옴
                
                if opinion:  # opinion이 비어있지 않을 때
                    for value in opinion:  # 여러 개의 행을 처리
                        team_opinion.append([row, value[0]])  # 첫 번째 컬럼 값을 리스트에 추가
            
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
                'team_opinion': team_opinion,
                'book_recommendation': book_recommendation
            })

    finally:
        user_conn.close()
        result_conn.close()
        
    return all_user_data

# ==================================  # 팀 의견
def draw_team_opinion(c, data, width, height, table_down):
    
    sub_result = summarize_subjective(data['team_opinion'])
    
    styles = getSampleStyleSheet()
    
    box_x, box_y = 50, height
    box_width, box_height = width-100, 340

    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(box_x, box_y, box_width, box_height, fill=1)

    # 텍스트 크기를 동적으로 조정
    text = "\n".join(sub_result)

    font_size = 12  # 초기 폰트 크기
    max_font_size = 12
    min_font_size = 8  # 최소 폰트 크기 (너무 작아지지 않도록 제한)

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
        
    paragraph.wrapOn(c, box_width - 20, box_height - 20)
    paragraph.drawOn(c, box_x + 10, box_y + (box_height - height_needed) / 2)  # 중앙 정렬

# ================================== # 도서 추천
def draw_book_recommendations(c, data, width, height_st2, table_down):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "NanumMyeongjo"
    style.fontSize = 10
    style.leading = 14
    style.alignment = 0

    x_start = 50  # 좌측 여백 (X 시작점)
    remaining_width = width - (2 * x_start)  # 페이지에서 좌우 여백을 제외한 너비
    box_width = remaining_width  # 박스의 총 너비
    box_padding = 10  # 박스 내부 여백
    box_y_start = height_st2 - table_down  # 박스가 시작되는 Y 좌표
    bottom_margin = 50  # 박스의 하단 여백
    box_height = box_y_start - bottom_margin  # 박스의 실제 높이
    title_height = 30  # "개선 방안" 제목 영역 높이

    # 두 번째 박스 - "개선 방안"
    box_x2 = x_start
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

    # 제목 박스 아래에 안내 문구 추가
    c.setFont("NanumMyeongjo", 11)
    c.setFillColor(colors.black)
    
    # 안내 문구를 위한 특별한 스타일
    guide_style = ParagraphStyle(
        'GuideText',
        fontName='NanumMyeongjo',
        fontSize=11,
        leading=14,
        alignment=1,  # 가운데 정렬
        textColor=colors.HexColor('#2C3E50'),  # 진한 남색
        spaceBefore=10,
        spaceAfter=10
    )
    
    guide_text = Paragraph(
        "피드백을 기반으로 AI가 도서 2개를 추천해드립니다", 
        guide_style
    )
    guide_text.wrapOn(c, box_width2 - 40, 30)
    guide_text.drawOn(c, box_x2 + 20, box_y_start - title_height - 25)
    
    # 시작 위치를 안내 문구 아래로 조정
    current_y = box_y_start - title_height - 60  # 기존 -30에서 -60으로 변경

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
    book_recommendations = data.get('book_recommendation', [])
    if not book_recommendations:
        return

    for i, book_info in enumerate(book_recommendations):
        if i > 0:  # 두 번째 책부터는 구분선 추가
            c.setStrokeColor(colors.grey)
            c.line(box_x2 + 10, current_y + 10, box_x2 + box_width2 - 10, current_y + 10)
            current_y -= 30

        # 1. 책 제목
        title = Paragraph(book_info.get('title', ''), title_style)
        title.wrapOn(c, box_width2 - 40, 30)
        title.drawOn(c, box_x2 + 20, current_y)
        current_y -= 25

        # 2. 저자
        authors = Paragraph(f"저자: {book_info.get('authors', '')}", text_style)
        authors.wrapOn(c, box_width2 - 40, 20)
        authors.drawOn(c, box_x2 + 20, current_y)
        current_y -= 25

        # 3. 책 이미지와 내용 요약을 나란히 배치
        img_width = 120
        img_height = 160
        image_y = current_y - img_height

        if book_info.get('thumbnail'):
            try:
                response = requests.get(book_info['thumbnail'])
                if response.status_code == 200:
                    img = ImageReader(BytesIO(response.content))
                    c.drawImage(img, box_x2 + 20, image_y, width=img_width, height=img_height)
            except Exception as e:
                print(f"이미지 로드 실패: {str(e)}")

        # 4. 내용 요약
        content_text = book_info.get('contents', '')
        # if len(content_text) > 300:
        #     content_text = content_text[:300] + "..."

        summary_x = box_x2 + 20 + img_width + 20
        summary_width = box_width2 - img_width - 60

        content = Paragraph(f"줄거리 및 내용 요약: \n{content_text}", text_style)
        content.wrapOn(c, summary_width, img_height)
        content.drawOn(c, summary_x, image_y + img_height - text_style.leading - 50)

        current_y = image_y - 40  # 다음 책을 위한 간격 조정

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
    height_st1 = 100
    height_st2 = height_st1 + 380  # 표 시작 위치
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
    draw_difference_chart(c, data, width, height_st2)
    draw_team_opinion(c, data, width, height_st1, table_down)
    
    # 새 페이지 추가
    c.showPage()
    
    # 두 번째 페이지에 도서 추천 정보 그리기
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName='NanumMyeongjo',
        fontSize=20,
        leading=24,
        alignment=1
    )
    
    # 제목 추가
    title = Paragraph("추천 도서", style)
    title.wrapOn(c, width-100, 40)
    title.drawOn(c, 50, height-70)
    
    # 도서 추천 정보 그리기 (전체 페이지 사용)
    draw_book_recommendations(c, data, width, height-100, 30)
    
    c.save()
    print(f"PDF 생성 완료: {filename}")
# ===================

if __name__ == "__main__":
    users_data = fetch_data()
    for user_data in users_data:
        user_data.update({
            'title': "인사고과 평가표",
        })

        filename = f"{user_data['username']}.pdf"
        generate_pdf(user_data, filename)
    
    # PDF 생성이 완료된 후 이메일 전송
    print("\n이메일을 전송 중입니다…")
    send_report_emails()
    print("이메일 전송을 완료했습니다.")