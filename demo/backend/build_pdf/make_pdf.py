import os
import platform
import sqlite3
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from io import BytesIO
from subprocess import run
from threading import Semaphore

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import requests.exceptions
from book_recommendation import find_lowest_keyword, get_book_recommendation
from feedback_summary import summarize_multiple, summarize_subjective
from load_book_chunk import load_all_book_chunks
from mail_service.send_email import send_report_emails
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

# OS별 폰트 경로 설정
if platform.system() == "Linux":
    font_path_regular = (
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"  # 나눔고딕 일반체
    )
    font_path_bold = (
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"  # 나눔고딕 볼드체
    )
else:
    raise RuntimeError("지원되지 않는 OS")

# 폰트 존재 여부 확인
if not os.path.exists(font_path_regular):
    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path_regular}")
if not os.path.exists(font_path_bold):
    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path_bold}")

# Matplotlib 폰트 적용
font_prop_regular = fm.FontProperties(fname=font_path_regular)
font_prop_bold = fm.FontProperties(fname=font_path_bold)

# ReportLab 폰트 적용
pdfmetrics.registerFont(TTFont("NanumGothic", font_path_regular))  # 일반 나눔고딕
pdfmetrics.registerFont(TTFont("NanumGothic-Bold", font_path_bold))  # 나눔고딕 볼드

# DB 및 경로 수정
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_DB_PATH = os.path.join(BASE_DIR, "db/user.db")
RESULT_DB_PATH = os.path.join(BASE_DIR, "db/result.db")
KEYWORD_DB_PATH = os.path.join(BASE_DIR, "db/feedback.db")
PDF_DIR = os.path.join(os.path.dirname(BASE_DIR), "pdf")


def run_script_if_file_not_exists(file_name, script_name):
    if not os.path.exists(file_name):
        run(["python", script_name])
    else:
        pass


def get_user_connection():
    return sqlite3.connect(USER_DB_PATH)


def get_result_connection():
    return sqlite3.connect(RESULT_DB_PATH)


def get_keyword_connection():
    return sqlite3.connect(KEYWORD_DB_PATH)


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
                    if hasattr(e, "args") and e.args and isinstance(e.args[0], dict):
                        error_info = e.args[0].get("error", {})
                        if error_info.get("code") == "too_many_requests":
                            time.sleep(wait)
                            tries -= 1
                            wait *= backoff_factor
                            continue
                    raise
            return func(*args, **kwargs)

        return wrapper

    return decorator_retry


# API 호출 시 동시 호출 제한 (최대 4개)
api_semaphore = Semaphore(4)


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
def call_get_book_recommendation(username, lowest_keyword):
    with api_semaphore:
        return get_book_recommendation(username, lowest_keyword)


# ==================================  # 로고 삽입
def draw_logo(c, width, height):
    """오른쪽 하단에 로고 이미지 추가하는 함수"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        image_dir = os.path.join(base_dir, "image_store")
        logo_path = os.path.join(image_dir, "logo.png")

        if not os.path.exists(logo_path):
            raise FileNotFoundError(f"로고 파일이 존재하지 않습니다: {logo_path}")

        c.drawImage(
            ImageReader(logo_path), width - 80, height - 810, width=40, height=40
        )
    except Exception as e:
        print(f"로고 이미지 삽입 실패: {e}")


# ==================================  '인사평가표 제목'
def draw_header(c, data, width, height):
    """인사고과 평가서 제목"""
    c.setFillColor(colors.black)
    c.setFont("NanumGothic-Bold", 30)
    c.drawCentredString(width / 2, height - 50, data["title"])


# ==================================  # 프로필사진, 개인정보, 등급
def draw_profile_box(c, data, width, height):
    """등급을 오른쪽 정렬하고, 정보와 맞추어 배치"""

    styles = getSampleStyleSheet()

    # 프로필 이미지 추가
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    image_dir = os.path.join(base_dir, "image_store")
    image_path = os.path.join(image_dir, "profile.png")
    img_width, img_height = 100, 100
    c.drawImage(
        ImageReader(image_path), 50, height - 80, width=img_width, height=img_height
    )

    # '개인정보' 제목
    c.setFont("NanumGothic-Bold", 15)
    c.drawString(180, height + 5, "정보")

    # 구분선
    line_x_start = 180  # 선의 시작 X 좌표
    line_x_end = 360  # 선의 끝 X 좌표 (길이 조절 가능)

    c.setStrokeColor(colors.black)  # 선 색상 설정
    c.setLineWidth(1)  # 선 두께 설정
    c.line(line_x_start, height, line_x_end, height)  # 선 그리기

    # 인적 사항(이름, 부서, 직급급) -> 표 형태
    c.setFont("NanumGothic", 14)
    info_x, info_y = 180, height - 35
    department, position = (
        data["position"].rsplit(" ", 1)
        if " " in data["position"]
        else (data["position"], "")
    )
    info_data = [["이름", data["name"]], ["부서", department], ["직급", position]]

    table = Table(info_data, colWidths=[50, 150])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), "NanumGothic"),
                ("FONTSIZE", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    table.wrapOn(c, width, height + 100)
    table.drawOn(c, info_x, info_y - 40)

    # 등급 제목 글씨 스타일 설정정
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="NanumGothic-Bold",
        fontSize=15,  # 등급 제목 크기 조정
        alignment=2,  # 오른쪽 정렬
        spaceAfter=5,  # 아래 간격 추가
    )

    # 등급 제목과 등급의 위치 조정
    line_x_start2 = width - 280  # 오른쪽 정렬 위치 (여백 조정 가능)
    title_y = height + 10  # '정보'와 같은 높이로 조정
    grade_y = title_y - 30  # 등급 아래 위치

    # 구분선
    c.setStrokeColor(colors.black)  # 선 색상 설정
    c.setLineWidth(1)  # 선 두께 설정
    c.line(line_x_start2 + 70, height, line_x_start2 + 240, height)  # 선 그리기

    # 등급(S, A, B, C, D) 스타일 설정정
    grade_style = ParagraphStyle(
        "GradeStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=50,  # 등급 크기
        textColor=colors.HexColor("#08c7b4"),  # 민트
        alignment=2,  # 오른쪽 정렬
    )

    title_paragraph = Paragraph("등급", title_style)  # 등급 제목
    grade_paragraph = Paragraph(data["grade"], grade_style)  # 등급(S, A, B, C, D)

    title_paragraph.wrapOn(c, 100, 30)  # 등급 제목 크기 조정
    title_paragraph.drawOn(c, line_x_start2, title_y)  # 등급 제목 위치 지정

    grade_paragraph.wrapOn(c, 100, 30)  # 등급(S, A, B, C, D) 크기 조정
    grade_paragraph.drawOn(
        c, line_x_start2 + 70, grade_y
    )  # 등급(S, A, B, C, D) 위치 지정


# ==================================  # 표, 막대그래프
def draw_table(c, data, width, height):
    table_data = [
        ["평가항목", "점수 (5점 만점)"],
        *data["scores"],
        ["합계", f"{data['total_score']:.2f}"],
    ]

    table = Table(table_data, colWidths=[115, 115])  # 열 너비 통일
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#08c7b4"),
                ),  # 헤더 배경색 (민트색)
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # 헤더 글씨색 (흰색)
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # 모든 셀 중앙 정렬
                ("FONTNAME", (0, 0), (-1, -1), "NanumGothic"),  # 폰트 적용
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    table.wrapOn(c, width, height)
    table.drawOn(c, 60, height - 40)


def draw_difference_chart(c, data, width, height):

    prop = fm.FontProperties(fname=font_path_regular, size=14)  # 없애도 될 듯..?

    # 데이터 준비
    labels = [score[0] for score in data["scores"]]
    values = np.array([float(score[1]) for score in data["scores"]])
    team_values = np.array([float(score[1]) for score in data["team_average"]])

    # 팀 평균 대비 차이 계산
    difference = values - team_values

    # 가장 잘한 항목과 가장 부족한 항목 찾기
    best_category = labels[np.argmax(difference)]
    worst_category = labels[np.argmin(difference)]

    # 그래프 크기 조정
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 색상 설정 (잘한 것은 초록색, 부족한 것은 빨간색 강조)
    colors = ["#08c7b4" if diff > 0 else "gray" for diff in difference]

    ax.barh(labels, difference, color=colors, alpha=0.7)
    ax.axvline(0, color="black", linewidth=1)  # 중앙선 추가

    # **텍스트 라벨 추가 (강점/약점 강조)**
    for i, (label, v) in enumerate(zip(labels, difference)):
        ha = "left" if v > 0 else "right"
        color = (
            "#08c7b4"
            if label == best_category
            else "gray" if label == worst_category else "black"
        )
        text = (
            "강점"
            if label == best_category
            else "약점" if label == worst_category else ""
        )
        # ax.text(v, i, f"{v:.1f}", ha=ha, va='center', fontsize=12, fontweight='bold', color='black', fontproperties=prop)  # 숫자
        ax.text(
            v + (0.1 if v > 0 else -0.2),
            i,
            text,
            ha=ha,
            va="center",
            fontsize=14,
            fontweight="bold",
            color=color,
            fontproperties=prop,
        )  # 강점/약점

    # X축 범위 자동 조정
    abs_max = max(abs(difference.min()), abs(difference.max()))
    ax.set_xlim(-abs_max - 0.5, abs_max + 0.5)

    # **그래프 상단에 "평균보다 낮음/높음" 표시 (더 크게 & 중앙 정렬)**
    ax.text(
        0,
        len(labels),
        "↓ 평균 이하 | 평균 이상 ↑",
        fontsize=14,
        color="black",
        fontweight="bold",
        ha="center",
        fontproperties=prop,
    )

    # **Y축 레이블 유지**
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontproperties=prop, fontsize=12)

    # 그리드 스타일 조정
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    # 그래프 저장 및 PDF 삽입
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100, facecolor="white", bbox_inches="tight")
    plt.close()
    buffer.seek(0)

    # PDF에 이미지 추가
    c.drawImage(ImageReader(buffer), width - 300, height - 70, width=250, height=180)


# ==================================  # 한줄 평가
def draw_assessment_box(c, data, width, height):

    mul_result = summarize_multiple(data["scores"])

    styles = getSampleStyleSheet()

    box_width, box_height = 490, 130  # 박스 크기 조정

    # 박스 그리기
    c.setFillColor(HexColor("#e9e9e9"))
    c.rect(
        width, height, box_width, box_height, fill=1, stroke=0
    )  # 회색 박스 위치, 크기, 채우기, 테두리 없음

    # 폰트 스타일
    style = ParagraphStyle(
        "CustomStyle",
        parent=styles["Normal"],
        fontName="NanumGothic",
        fontSize=12,
        leading=14,
    )
    paragraph = Paragraph(mul_result, style)

    # 텍스트 박스 내 중앙 정렬
    paragraph.wrapOn(c, box_width - 20, box_height - 20)
    paragraph.drawOn(c, width + 10, height + 70)


# ==================================  # 팀 의견 (주관식 요약)
def draw_team_opinion(c, data, width, height):

    sub_result = summarize_subjective(data["team_opinion"])

    # ID와 키워드를 매핑한 딕셔너리 생성
    id_to_keyword = {item["id"]: item["keyword"] for item in data["feedback_keywords"]}

    # keyword 기준으로 결과를 저장할 딕셔너리
    keyword_to_responses = defaultdict(list)

    # sub_result를 순회하며 keyword별 response 그룹화
    for entry in sub_result:
        question_str = entry["question"]
        question_id = int(
            question_str.split("_")[1]
        )  # question에서 숫자 부분만 추출하여 정수 변환
        keyword = id_to_keyword.get(
            question_id
        )  # 해당 ID가 feedback_keywords에 있는지 확인

        if keyword:
            keyword_to_responses[keyword].append(entry["response"])

    # keyword별 response 합치기
    merged_results = [
        {"keyword": keyword, "response": " ".join(responses)}
        for keyword, responses in keyword_to_responses.items()
    ]

    # ======== 글꼴 준비 ========
    # 페이지 여백 설정 (상하좌우)
    left_margin = 50
    right_margin = 50
    top_margin = 50
    bottom_margin = 50

    # 텍스트가 출력 가능한 영역 너비
    text_width = width - left_margin - right_margin
    x = left_margin
    y = height - top_margin

    # 제목(키워드 별 평가) 스타일 정의
    header_style = ParagraphStyle(
        "Header",
        fontName="NanumGothic-Bold",
        fontSize=17,
        leading=22,
        alignment=TA_LEFT,
    )
    # Paragraph 스타일 정의
    keyword_style = ParagraphStyle(
        "Keyword",
        fontName="NanumGothic-Bold",
        fontSize=12,  # 수정 2
        leading=16,  # 줄 간격 15
        alignment=TA_LEFT,
        backColor=colors.HexColor("#E8F6F3"),
    )
    response_style = ParagraphStyle(
        "Response",
        fontName="NanumGothic",
        fontSize=12,
        leading=15,  # 14
        alignment=TA_LEFT,
    )

    # 항목 간 간격 및 구분선 관련 설정
    space_after_keyword = 5  # keyword 출력 후 간격
    space_after_response = 30  # response 출력 후 다음 항목과의 간격

    # ======== pdf에 삽입 ========

    header_text = "키워드별 평가"
    p_header = Paragraph(header_text, header_style)
    w_header, h_header = p_header.wrap(text_width, height)

    p_header.drawOn(c, x, y - h_header)
    y -= h_header + 10  # 제목 아래 10pt 간격
    # 제목 아래 구분선 추가
    c.setLineWidth(1)
    c.line(x, y, x + text_width, y)
    y -= 10  # 구분선 아래 10pt 간격

    for item in merged_results:
        keyword = item.get("keyword", "")
        response = item.get("response", "")

        # Paragraph 객체 생성
        p_keyword = Paragraph(keyword, keyword_style)
        p_response = Paragraph(response, response_style)

        # wrap() 호출을 통해 출력 영역 내에서 문단의 크기를 산출 (너비, 높이)
        _, keyword_height = p_keyword.wrap(text_width, height)
        _, response_height = p_response.wrap(text_width, height)

        # 한 항목(block)이 차지할 총 높이 계산
        total_needed = (
            keyword_height
            + space_after_keyword
            + response_height
            + space_after_response
        )

        # 남은 공간이 부족하면 새 페이지 추가
        if y - total_needed < bottom_margin:
            c.showPage()
            y = height - top_margin

        # keyword 출력
        p_keyword.drawOn(c, x, y - keyword_height)
        y -= keyword_height + space_after_keyword

        # response 출력
        p_response.drawOn(c, x, y - response_height)
        y -= response_height + space_after_response


# ================================== # 도서 추천
def draw_book_recommendations(c, data, width, height_st2, table_down):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "NanumGothic"
    style.fontSize = 12
    style.leading = 14
    style.alignment = 0

    x_start = 50  # 좌측 여백 (X 시작점)
    remaining_width = width - (2 * x_start)  # 페이지에서 좌우 여백을 제외한 너비
    box_width = remaining_width  # 박스의 총 너비
    box_padding = 10  # 박스 내부 여백
    box_y_start = height_st2 - table_down  # 박스가 시작되는 Y 좌표
    bottom_margin = 100  # 박스의 하단 여백
    box_height = box_y_start - bottom_margin  # 박스의 실제 높이
    title_height = 30  # 제목 영역 높이

    # 두 번째 박스 - "개선 방안"
    box_x2 = x_start
    box_width2 = box_width - box_padding / 2

    # 박스 그리기
    c.setStrokeColor(colors.black)
    c.setFillColor(HexColor("#E2E2E2"))  # 배경색 변경
    c.rect(box_x2, bottom_margin, box_width2, box_height, fill=0)

    # 제목 박스
    c.setFillColor(colors.HexColor("#E8F6F3"))  # 민트색으로 변경
    c.rect(box_x2, box_y_start - title_height, box_width2, title_height, fill=1)

    c.setFont("NanumGothic-Bold", 12)
    c.setFillColor(colors.black)  # 텍스트 색상을 흰색으로 변경
    c.drawCentredString(
        box_x2 + box_width2 / 2,
        box_y_start - title_height / 2 - 6,
        "피드백을 기반으로 AI가 도서 3개를 추천해드립니다",
    )

    # 시작 위치를 제목 박스 바로 아래로 조정
    current_y = (
        box_y_start - title_height - 60
    )  # 가이드 텍스트 관련 코드 제거로 위치 조정

    # 텍스트 스타일 설정
    title_style = ParagraphStyle(
        "BookTitle",
        fontName="NanumGothic-Bold",
        fontSize=12,
        leading=16,
        spaceBefore=0,
        spaceAfter=5,
    )

    text_style = ParagraphStyle(
        "BookInfo",
        fontName="NanumGothic",
        fontSize=10,
        leading=14,
        spaceBefore=0,
        spaceAfter=5,
    )

    # 도서 추천 정보 표시
    book_recommendations = data.get("book_recommendation", [])
    if not book_recommendations:
        return

    # 시작 위치 설정
    content_x = box_x2 + 20
    current_y = box_y_start - title_height - 50

    for i, book_info in enumerate(book_recommendations[:3]):  # 상위 3개만 처리
        if i > 0:  # 두 번째 책부터는 구분선 추가
            c.setStrokeColor(colors.grey)
            c.line(
                box_x2 + 10, current_y + 10, box_x2 + box_width2 - 10, current_y + 10
            )
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

        if book_info.get("thumbnail"):
            try:
                response = requests.get(book_info["thumbnail"])
                if response.status_code == 200:
                    img = ImageReader(BytesIO(response.content))
                    c.drawImage(
                        img, content_x, image_y, width=img_width, height=img_height
                    )
            except Exception as e:
                print(f"이미지 로드 실패: {str(e)}")

        # 4. 내용 요약
        content_text = book_info.get("contents", "")

        summary_x = content_x + img_width + 20
        summary_width = box_width2 - img_width - 60

        content = Paragraph(f":\n{content_text}", text_style)
        content.wrapOn(c, summary_width, img_height)
        content.drawOn(c, summary_x, image_y + img_height - text_style.leading - 65)

        current_y = image_y - 40  # 다음 책을 위한 간격 조정

        # 페이지 크기를 초과하지 않도록 체크
        if current_y < bottom_margin + 50:  # 여백 체크값
            break


# 페이지 번호를 그리는 함수
def draw_page_number(c, width, margin=36):
    page_num = c.getPageNumber()
    c.setFillColor(colors.black)
    c.setFont("NanumGothic", 10)
    c.drawCentredString(width / 2, 36, str(page_num))


# ==================================


# 데이터베이스 최적화 적용한 사용자 데이터 가져오기
def fetch_data():
    user_conn = get_user_connection()
    result_conn = get_result_connection()
    keyword_conn = get_keyword_connection()
    try:
        user_cur = user_conn.cursor()
        user_cur.execute(
            "SELECT username, name, group_id, rank FROM users WHERE role = 'user'"
        )
        users = user_cur.fetchall()
        # 그룹 정보를 한 번에 조회
        user_cur.execute("SELECT id, group_name FROM groups")
        groups = {row[0]: row[1] for row in user_cur.fetchall()}

        result_cur = result_conn.cursor()
        result_cur.execute("PRAGMA table_info(multiple)")
        all_columns = [col[1] for col in result_cur.fetchall()]
        mul_columns = [
            col
            for col in all_columns
            if col not in ("id", "to_username", "총합", "등급", "created_at")
        ]
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
            placeholders = ",".join("?" for _ in usernames)
            query = f"SELECT * FROM multiple WHERE to_username IN ({placeholders})"
            result_cur.execute(query, usernames)
            multiple_rows = result_cur.fetchall()
        else:
            multiple_rows = []
        multiple_by_user = {}
        if multiple_rows:
            col_idx = {col: idx for idx, col in enumerate(all_columns)}
            for row in multiple_rows:
                uname = row[col_idx["to_username"]]
                multiple_by_user[uname] = row

        # 사용자별 주관식 피드백을 한 번에 조회
        if usernames:
            placeholders = ",".join("?" for _ in usernames)
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
                subjective_by_user[data.get("to_username")].append(data)

        # 피드백 키워드는 한 번만 조회
        keyword_cur = keyword_conn.cursor()
        keyword_cur.execute("SELECT id, keyword FROM feedback_questions")
        feedback_keywords = [
            {"id": r[0], "keyword": r[1]} for r in keyword_cur.fetchall()
        ]

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
                    if (
                        key not in ("id", "to_username", "created_at")
                        and value is not None
                    ):
                        team_opinion.append([key, value])
            all_user_data.append(
                {
                    "username": username,
                    "name": name,
                    "position": position,
                    "grade": grade,
                    "scores": scores,
                    "team_average": team_average,
                    "total_score": total_score,
                    "team_opinion": team_opinion,
                    "feedback_keywords": feedback_keywords,
                    "lowest_keyword": lowest_keyword,
                    "title": "인사고과 평가표",
                }
            )
    finally:
        user_conn.close()
        result_conn.close()
        keyword_conn.close()
    return all_user_data


def generate_pdf(data, filename):
    # pdf 디렉토리가 없으면 생성
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)

    # pdf 디렉토리 안에 파일 생성
    filepath = os.path.join(PDF_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # ========첫번째 페이지(타이틀, 사진, 개인정보, 등급, 표, 막대그래프, 한줄평가)========
    background_color = colors.white  # 배경색 설정
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)

    draw_header(c, data, width, height - 50)
    draw_profile_box(c, data, width, height - 180)

    # 구분선 그리기
    c.setFillColor(colors.black)
    c.setFont("NanumGothic-Bold", 17)
    c.drawCentredString(95, height - 310, "종합 평가")
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height - 320, width - 40, height - 320)

    draw_table(c, data, width, height - 450)
    draw_difference_chart(c, data, width, height - 450)

    # 구분선 그리기
    c.setFillColor(colors.black)
    c.setFont("NanumGothic-Bold", 17)
    c.drawCentredString(95, height - 550, "한줄 평가")
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height - 560, width - 40, height - 560)

    draw_assessment_box(c, data, 60, height - 700)
    draw_logo(c, width, height)
    draw_page_number(c, width)

    # ========두번째 페이지(키워드 별 주관식 요약)========
    c.showPage()
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)

    draw_team_opinion(c, data, width, height)
    draw_logo(c, width, height)
    draw_page_number(c, width)

    # ========세번째 페이지(도서 추천)========
    c.showPage()
    c.setFillColor(background_color)
    c.rect(0, 0, width, height, fill=1)

    # '종합 평가'와 동일한 스타일로 '추천 도서' 제목 추가
    c.setFillColor(colors.black)
    c.setFont("NanumGothic-Bold", 17)
    c.drawString(50, height - 70, "추천 도서")
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height - 80, width - 50, height - 80)
    draw_logo(c, width, height)

    # 도서 추천 정보 그리기 (간격 줄임)
    draw_book_recommendations(c, data, width, height - 100, 10)
    draw_page_number(c, width)

    c.save()


# ===================


# -------------------------------
# 개별 사용자의 데이터를 받아 도서 추천 API 호출 및 PDF 생성
def process_user(user_data):
    username = user_data["username"]
    lowest_keyword = user_data.get("lowest_keyword")
    if not lowest_keyword:
        user_data["book_recommendation"] = None
    else:
        recommendation = call_get_book_recommendation(username, lowest_keyword)
        user_data["book_recommendation"] = recommendation
    filename = f"{username}.pdf"
    generate_pdf(user_data, filename)
    print(f"[{username}] 보고서 생성 완료")
    return username


if __name__ == "__main__":
    # 청크 파일을 미리 메모리에 로드
    load_all_book_chunks()
    users_data = fetch_data()
    # CPU 수에 따라 최대 워커 수 조정
    max_workers = min(os.cpu_count() or 4, 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_user, user_data) for user_data in users_data]
        for future in as_completed(futures):
            try:
                _ = future.result()
            except Exception as e:
                print(f"Error processing user: {e}")
    send_report_emails()
