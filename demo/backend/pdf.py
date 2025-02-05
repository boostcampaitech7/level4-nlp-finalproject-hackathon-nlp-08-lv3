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
import platform
from subprocess import run
from llm_sum import summarize_multiple, summarize_subjective
import requests.exceptions
from book_recommendation import get_book_recommendation, find_lowest_keyword
from send_email import send_report_emails
from collections import defaultdict


# OS별 폰트 경로 설정
if platform.system() == "Linux":
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"  # 리눅스 폰트 경로
else:
    raise RuntimeError("지원되지 않는 OS")

# 폰트가 존재하는지 확인
if not os.path.exists(font_path):
    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")

# Matplotlib 폰트 적용
font_prop = fm.FontProperties(fname=font_path)

# ReportLab 폰트 등록
pdfmetrics.registerFont(TTFont("NanumGothic", font_path))

# DB 경로 설정과 함께 book_chunk 경로도 설정
USER_DB_PATH = os.path.join(os.path.dirname(__file__), "db/user.db")
RESULT_DB_PATH = os.path.join(os.path.dirname(__file__), "db/result.db")
KEYWORD_DB_PATH = os.path.join(os.path.dirname(__file__), "db/feedback.db")
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

def get_keyword_connection():
    return sqlite3.connect(KEYWORD_DB_PATH)

# ==================================  # 사용자 정보 가져오기
def fetch_data():
    user_conn = get_user_connection()
    result_conn = get_result_connection()
    keyword_conn = get_keyword_connection()

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
            
            # 주관식 키워드 가져오기
            keyword_cur = keyword_conn.cursor()
            keyword_cur.execute("SELECT id, keyword FROM feedback_questions")
            feedback_keywords = [{"id": row[0], "keyword": row[1]} for row in keyword_cur.fetchall()]
            
            # 주관식 답변 가져오기
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
                'feedback_keywords': feedback_keywords,
                'book_recommendation': book_recommendation
            })

    finally:
        user_conn.close()
        result_conn.close()
        
    return all_user_data

# ==================================  '인사평가표 제목'
def draw_header(c, data, width, height):
    """ 인사고과 평가서 제목 """
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 30)
    c.drawCentredString(width / 2, height - 50, data['title'])

# ==================================  # 프로필사진, 개인정보, 등급
def draw_profile_box(c, data, width, height):
    """ 등급을 오른쪽 정렬하고, 정보와 맞추어 배치 """
    
    styles = getSampleStyleSheet()
    
    # 프로필 이미지 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "profile.png")
    img_width, img_height = 100, 100
    c.drawImage(ImageReader(image_path), 50, height-80, width=img_width, height=img_height)


    # '개인정보' 제목
    c.setFont("NanumGothic", 15)
    c.drawString(180, height + 5, "정보")

    # 구분선 추가 (가로 선)
    line_x_start = 180  # 선의 시작 X 좌표
    line_x_end = 360  # 선의 끝 X 좌표 (길이 조절 가능)

    c.setStrokeColor(colors.black)  # 선 색상 설정
    c.setLineWidth(1)  # 선 두께 설정
    c.line(line_x_start, height, line_x_end, height)  # 선 그리기

    # 인적 사항을 표 형태로 정렬
    c.setFont("NanumGothic", 14)
    info_x, info_y = 180, height - 35
    department, position = data['position'].rsplit(" ", 1) if " " in data['position'] else (data['position'], "")
    info_data = [["이름", data['name']], 
                 ["부서", department],
                 ["직급", position]]
    
    table = Table(info_data, colWidths=[50, 150])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'NanumGothic'),
        ('FONTSIZE', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    table.wrapOn(c, width, height+100)
    table.drawOn(c, info_x, info_y - 40)
    
    
    # "등급"을 오른쪽 정렬 및 폰트 크기 15 적용
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=15,  # 등급 제목 크기 조정
        alignment=2,  # 오른쪽 정렬
        spaceAfter=5,  # 아래 간격 추가
    )
    
    # '등급'과 등급의 위치 조정 (정보와 맞춤)
    line_x_start2 = width - 280  # 오른쪽 정렬 위치 (여백 조정 가능)
    title_y = height + 10  # '정보'와 같은 높이로 조정
    grade_y = title_y - 30  # 등급 아래 위치
    
    # 구분선 추가
    c.setStrokeColor(colors.black)  # 선 색상 설정
    c.setLineWidth(1)  # 선 두께 설정
    c.line(line_x_start2 + 70, height, line_x_start2 + 240, height)  # 선 그리기
    
    # 등급 값을 스타일 적용하여 표시 (네이비 색상)
    grade_style = ParagraphStyle(
        "GradeStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=50,  # 등급 크기
        textColor=colors.HexColor("#08c7b4"),  # 민트트 색상 적용
        alignment=2,  # 오른쪽 정렬
    )

    title_paragraph = Paragraph("등급", title_style)
    grade_paragraph = Paragraph(data['grade'], grade_style)
    
    title_paragraph.wrapOn(c, 100, 30)  # 제목 크기 조정
    title_paragraph.drawOn(c, line_x_start2, title_y)  # 제목 위치 지정
    
    grade_paragraph.wrapOn(c, 100, 30)  # 등급 크기 조정
    grade_paragraph.drawOn(c, line_x_start2 + 70, grade_y)  # 등급 위치 지정

# ==================================  # 표, 막대그래프
def draw_table(c, data, width, height):
    table_data = [
        ["평가항목", "점수 (5점 만점)"],
        *data['scores'],
        ["합계", f"{data['total_score']:.2f}"]
    ]
    
    table = Table(table_data, colWidths=[130, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#08c7b4")), # 민트트
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
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # 색상 설정 (잘한 것은 초록색, 부족한 것은 빨간색 강조)
    colors = ['#08c7b4' if diff > 0 else 'gray' for diff in difference]
    
    ax.barh(labels, difference, color=colors, alpha=0.7)
    ax.axvline(0, color='black', linewidth=1)  # 중앙선 추가

    # **텍스트 라벨 추가 (강점/약점 강조)**
    for i, (label, v) in enumerate(zip(labels, difference)):
        ha = 'left' if v > 0 else 'right'
        color = '#08c7b4' if label == best_category else "gray" if label == worst_category else "black"
        text = "강점" if label == best_category else "약점" if label == worst_category else ""
        # ax.text(v, i, f"{v:.1f}", ha=ha, va='center', fontsize=12, fontweight='bold', color='black', fontproperties=prop)  # 숫자
        ax.text(v + (0.1 if v > 0 else -0.2), i, text, ha=ha, va='center', fontsize=14, fontweight='bold', color=color, fontproperties=prop)  # 강점/약점

    # X축 범위 자동 조정
    abs_max = max(abs(difference.min()), abs(difference.max()))
    ax.set_xlim(-abs_max - 0.5, abs_max + 0.5)

    # **그래프 상단에 "평균보다 낮음/높음" 표시 (더 크게 & 중앙 정렬)**
    ax.text(0, len(labels), "↓ 평균 이하 | 평균 이상 ↑", fontsize=14, color="black", fontweight="bold", ha="center", fontproperties=prop)

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
    c.drawImage(ImageReader(buffer), width-280, height-90, width=250, height=180)
    
# ==================================  # 한줄평가
def draw_assessment_box(c, data, width, height):
    
    mul_result = summarize_multiple(data['scores'])
    
    styles = getSampleStyleSheet()

    box_width, box_height = 500, 190  # 박스 크기 조정

    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.lightgrey)
    c.rect(width, height, box_width, box_height, fill=1)

    # 폰트 스타일
    style = ParagraphStyle(
        "CustomStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=11,
        leading=14
    )
    paragraph = Paragraph(mul_result, style)

    # 텍스트 박스 내 중앙 정렬
    paragraph.wrapOn(c, box_width - 10, box_height - 10)
    paragraph.drawOn(c, width + 5, height + 20)
    
# ==================================  # 팀 의견 (주관식 요약)
def draw_team_opinion(c, data, width, height):
    
    sub_result = summarize_subjective(data['team_opinion'])
    
    # ID와 키워드를 매핑한 딕셔너리 생성
    id_to_keyword = {item['id']: item['keyword'] for item in data['feedback_keywords']}

    # keyword 기준으로 결과를 저장할 딕셔너리
    keyword_to_responses = defaultdict(list)
    
    # sub_result를 순회하며 keyword별 response 그룹화
    for entry in sub_result:
        question_str = entry['question']
        question_id = int(question_str.split('_')[1])  # question에서 숫자 부분만 추출하여 정수 변환
        keyword = id_to_keyword.get(question_id)  # 해당 ID가 feedback_keywords에 있는지 확인
        
        if keyword:
            keyword_to_responses[keyword].append(entry['response'])
            
    # keyword별 response 합치기
    merged_results = [
        {'keyword': keyword, 'response': ' '.join(responses)}
        for keyword, responses in keyword_to_responses.items()
    ]
    
    styles = getSampleStyleSheet()
    
    box_x, box_y = 50, height
    box_width, box_height = width-100, 390

    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.white)
    c.rect(box_x, box_y, box_width, box_height, fill=1)

    # 텍스트 크기를 동적으로 조정
    text = ""
    for response_dict in merged_results:  # merged_results은 딕셔너리 {'keyword':'', 'response':''}
        text += f"<b>{response_dict['keyword']}</b><br/>"  # 키워드는 굵게 표시
        text += response_dict['response'] + "<br/><br/>"

    font_size = 12  # 초기 폰트 크기
    max_font_size = 12
    min_font_size = 9  # 최소 폰트 크기 (너무 작아지지 않도록 제한)

    while font_size >= min_font_size:
        style = ParagraphStyle(
            "CustomStyle",
            parent=styles["Normal"],
            fontName="NanumGothic",
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
    style.fontName = "NanumGothic"
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

    c.setFont("NanumGothic", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(
        box_x2 + box_width2 / 2,
        box_y_start - title_height / 2 - 6,
        "개선 방안"
    )

    # 제목 박스 아래에 안내 문구 추가
    c.setFont("NanumGothic", 11)
    c.setFillColor(colors.black)
    
    # 안내 문구를 위한 특별한 스타일
    guide_style = ParagraphStyle(
        'GuideText',
        fontName='NanumGothic',
        fontSize=11,
        leading=14,
        alignment=1,  # 가운데 정렬
        textColor=colors.HexColor('#2C3E50'),  # 진한 남색
        spaceBefore=10,
        spaceAfter=10
    )
    
    guide_text = Paragraph(
        "피드백을 기반으로 AI가 도서 3개를 추천해드립니다", 
        guide_style
    )
    guide_text.wrapOn(c, box_width2 - 40, 30)
    guide_text.drawOn(c, box_x2 + 20, box_y_start - title_height - 25)
    
    # 시작 위치를 안내 문구 아래로 조정
    current_y = box_y_start - title_height - 60  # 기존 -30에서 -60으로 변경

    # 텍스트 스타일 설정
    title_style = ParagraphStyle(
        'BookTitle',
        fontName='NanumGothic',
        fontSize=12,
        leading=16,
        spaceBefore=0,
        spaceAfter=5
    )
    
    text_style = ParagraphStyle(
        'BookInfo',
        fontName='NanumGothic',
        fontSize=10,
        leading=14,
        spaceBefore=0,
        spaceAfter=5
    )

    # 도서 추천 정보 표시
    book_recommendations = data.get('book_recommendation', [])
    if not book_recommendations:
        return
    
    # 시작 위치 설정
    content_x = box_x2 + 20
    current_y = box_y_start - title_height - 50

    for i, book_info in enumerate(book_recommendations[:3]):  # 상위 3개만 처리
        if i > 0:  # 두 번째 책부터는 구분선 추가
            c.setStrokeColor(colors.grey)
            c.line(box_x2 + 10, current_y + 10, box_x2 + box_width2 - 10, current_y + 10)
            current_y -= 30

        # 1. 책 제목과 유사도
        title_text = f"{book_info.get('title', '')}"
        title = Paragraph(title_text, title_style)
        title.wrapOn(c, box_width2 - 40, 30)
        title.drawOn(c, content_x, current_y)
        current_y -= 25

        # 2. 저자
        authors = Paragraph(f"저자: {book_info.get('authors', '')}", text_style)
        authors.wrapOn(c, box_width2 - 40, 20)
        authors.drawOn(c, content_x, current_y)
        current_y -= 15

        # 3. 책 이미지와 내용 요약을 나란히 배치
        img_width = 60
        img_height = 80
        image_y = current_y - img_height

        if book_info.get('thumbnail'):
            try:
                response = requests.get(book_info['thumbnail'])
                if response.status_code == 200:
                    img = ImageReader(BytesIO(response.content))
                    c.drawImage(img, content_x, image_y, width=img_width, height=img_height)
            except Exception as e:
                print(f"이미지 로드 실패: {str(e)}")

        # 4. 내용 요약
        content_text = book_info.get('contents', '')
        # if len(content_text) > 300:
        #     content_text = content_text[:300] + "..."

        summary_x = content_x + img_width + 20
        summary_width = box_width2 - img_width - 60

        content = Paragraph(f"내용 요약:\n{content_text}", text_style)
        content.wrapOn(c, summary_width, img_height)
        content.drawOn(c, summary_x, image_y + img_height - text_style.leading - 65)

        current_y = image_y - 40  # 다음 책을 위한 간격 조정

        # 페이지 크기를 초과하지 않도록 체크
        if current_y < bottom_margin + 50:  # 여백보다 낮아지면 중단
            break

# ==================================
def generate_pdf(data, filename):
    # pdf 디렉토리가 없으면 생성
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
        
    # pdf 디렉토리 안에 파일 생성
    filepath = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # ========첫번째 페이지(타이틀, 사진, 개인정보, 등급, 표, 막대그래프, 한줄평가)========
    # === 🟢 배경 색 변경 ===
    background_color = colors.white
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    
    draw_header(c, data, width, height - 50)   
    draw_profile_box(c, data, width, height - 180)
    
    height_st = height - 350
    # 구분선 그리기
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 20)
    c.drawCentredString(90, height_st + 10, '종합 평가')
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height_st, width - 50, height_st)
    
    draw_table(c, data, width, height_st - 100)
    draw_difference_chart(c, data, width, height_st - 100)
    
    draw_assessment_box(c, data, 50, 80)
    
    # ========두번째 페이지(키워드 별 주관식 요약)========
    c.showPage()
    # === 🟢 배경 색 변경 ===
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    
    draw_team_opinion(c, data, width, 50)
    
    # ========세번째 페이지(도서 추천)========
    c.showPage()
     # === 🟢 배경 색 변경 ===
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)
    
    # 데이터에 도서 추천 정보가 없는 경우 기본값 설정
    if 'book_recommendation' not in data:
        data['book_recommendation'] = "도서 추천 정보를 찾을 수 없습니다."
    # 세번째 페이지에 도서 추천 정보 그리기
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName='NanumGothic',
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