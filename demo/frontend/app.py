from modules.login import login_page
from modules.account import create_account_page, account_created_page
from modules.admin_questions import admin_manage_questions, preview_questions, question_add_page, question_edit_page
from modules.admin_feedback import admin_view_feedback
from modules.user_feedback_write import user_write_feedback
from modules.user_feedback_result import user_view_my_feedback
from modules.upload_files import question_add_from_pdf_page
from modules.admin_group_manage import admin_manage_groups
import time
import streamlit as st
from dotenv import load_dotenv
import requests

from streamlit_option_menu import option_menu

load_dotenv()

API_BASE_URL = "http://localhost:5000/api"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "name" not in st.session_state:
    st.session_state.name = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "account_created" not in st.session_state:
    st.session_state.account_created = False


def main():
    st.set_page_config(page_title="동료 피드백 플랫폼", layout="wide")

    if st.session_state.account_created:
        account_created_page()
    elif st.session_state.page == "login":
        if not st.session_state.logged_in:
            login_page()
        else:
            if st.session_state.role == "admin":
                admin_page()
            else:
                user_page()
    elif st.session_state.page == "create_account":
        create_account_page()
    elif st.session_state.page == "question_add":
        question_add_page()
    elif st.session_state.page == "question_edit":
        question_edit_page(st.session_state.edit_question_id)
    elif st.session_state.page == "question_add_from_pdf":
        question_add_from_pdf_page()
    elif st.session_state.page == "admin_manage_questions": # 파일로 질문 추가 페이지 -> 리뷰 관리 페이지 이동
        admin_page(1)  # 리뷰 관리 페이지 호출
    else:
        st.session_state.page = "login"
        st.stop()

def admin_page(tab = 0): # admin_page로 돌아갈 때 돌아갈 tab을 정하기 위해 변수 추가
    # 초기 상태값 설정
    if "admin_tab" not in st.session_state:
        st.session_state.admin_tab = "mypage"

    with st.sidebar:
        # 📌 사용자 메뉴 생성 (마이페이지 추가)
        choice = option_menu("관리자 메뉴", ["마이페이지", "리뷰 관리", "리뷰 결과 분석", "부서 관리", "로그아웃"],
                            icons=['person-circle', 'list-check', 'clipboard-check', 'person-add', 'box-arrow-right'],
                            menu_icon="app-indicator", default_index=tab, # 여기로 받아서 tab 바꿀 수 있음
                            styles={
                                "container": {"padding": "4!important", "background-color": "#fafafa"},
                                "icon": {"color": "black", "font-size": "25px"},
                                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px",
                                            "--hover-color": "#fafafa"},
                                "nav-link-selected": {"background-color": "#08c7b4"},
                            })

    # 📌 선택된 메뉴에 따라 동작
    if choice == "마이페이지":
        st.session_state.admin_tab = "mypage"
    elif choice == "리뷰 관리":
        st.session_state.admin_tab = "questions"
    elif choice == "리뷰 결과 분석":
        st.session_state.admin_tab = "feedback"
    elif choice == "부서 관리":
        st.session_state.admin_tab = "groups"    
    elif choice == "로그아웃":
        do_logout()
        st.experimental_rerun()

    # 관리자 정보 조회
    response = requests.get(f"{API_BASE_URL}/users")
    current_admin = None

    if response.status_code == 200 and response.json().get("success"):
        users = response.json()["users"]
        current_admin = next((user for user in users if user["username"] == st.session_state.username), None)

    # 관리자 정보 저장 (이메일 정보 포함)
    admin_email = current_admin.get("email", "이메일 없음") if current_admin else "이메일 없음"
    admin_name = st.session_state.name if "name" in st.session_state else "이름 없음"
    admin_role = "관리자"

    if st.session_state.admin_tab == "mypage":
        st.subheader("👤 마이페이지")
        
        # CSS 스타일 추가
        st.markdown("""
        <style>
        .user-info-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .info-header {
            color: #1f1f1f;
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .info-content {
            color: #08c7b4;
            font-size: 1.1em;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

        # 3개의 컬럼으로 나누어 정보 표시
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">👤 이름</div>
                <div class="info-content">{}</div>
            </div>
            """.format(admin_name), unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">🎯 역할</div>
                <div class="info-content">{}</div>
            </div>
            """.format(admin_role), unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">📧 이메일</div>
                <div class="info-content">{}</div>
            </div>
            """.format(admin_email), unsafe_allow_html=True)

    elif st.session_state.admin_tab == "questions":
        admin_manage_questions()
    elif st.session_state.admin_tab == "feedback":
        admin_view_feedback()
### 그룹 수정 시작
    elif st.session_state.admin_tab == "groups":
        admin_manage_groups()
### 그룹 수정 끝

def user_page():
    # 사용자 정보 조회
    response = requests.get(f"{API_BASE_URL}/users")
    current_user = None

    if response.status_code == 200 and response.json().get("success"):
        users = response.json()["users"]
        current_user = next((user for user in users if user["username"] == st.session_state.username), None)

    # 사용자 정보 저장
    group_name = current_user.get("group_name", "소속 없음") if current_user else "소속 없음"
    rank = current_user.get("rank", "직급 없음") if current_user else "직급 없음"
    user_name = st.session_state.name if "name" in st.session_state else "이름 없음"
    user_email = current_user.get("email", "이메일 없음") if current_user else "이메일 없음"

    # 초기 상태값 설정
    if "user_tab" not in st.session_state:
        st.session_state.user_tab = "mypage"

    with st.sidebar:
        # 📌 사용자 메뉴 생성 (마이페이지 추가)
        choice = option_menu("사용자 메뉴", ["마이페이지", "리뷰 작성", "리뷰 결과", "로그아웃"],
                            icons=['person-circle', 'pencil-square', 'clipboard-check', 'box-arrow-right'],
                            menu_icon="app-indicator", default_index=0,
                            styles={
                                "container": {"padding": "4!important", "background-color": "#fafafa"},
                                "icon": {"color": "black", "font-size": "25px"},
                                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px",
                                            "--hover-color": "#fafafa"},
                                "nav-link-selected": {"background-color": "#08c7b4"},
                            })

    # 📌 선택된 메뉴에 따라 동작
    if choice == "마이페이지":
        st.session_state.user_tab = "mypage"
    elif choice == "리뷰 작성":
        st.session_state.user_tab = "write"
    elif choice == "리뷰 결과":
        st.session_state.user_tab = "my_feedback"
    elif choice == "로그아웃":
        do_logout()
        st.experimental_rerun()

    # 리뷰 통계 데이터 가져오기
    written_reviews = 0
    received_reviews = 0
    
    try:
        # 작성한 리뷰 수 조회
        written_response = requests.get(
            f"{API_BASE_URL}/feedback/count/written/{st.session_state.user_id}"
        )
        if written_response.status_code == 200 and written_response.json().get("success"):
            written_reviews = written_response.json().get("count", 0)
            
        # 받은 리뷰 수 조회
        received_response = requests.get(
            f"{API_BASE_URL}/feedback/count/received/{st.session_state.user_id}"
        )
        if received_response.status_code == 200 and received_response.json().get("success"):
            received_reviews = received_response.json().get("count", 0)
    except Exception as e:
        st.error("통계 데이터를 가져오는 중 오류가 발생했습니다.")
        print(f"Error fetching review statistics: {e}")

    # 📌 마이페이지 - 사용자 정보 표시
    if st.session_state.user_tab == "mypage":
        st.subheader("👤 마이페이지")
        
        # CSS 스타일 추가
        st.markdown("""
        <style>
        .user-info-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .info-header {
            color: #1f1f1f;
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .info-content {
            color: #08c7b4;
            font-size: 1.1em;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)

        # 4개의 컬럼으로 나누어 정보 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">👥 소속</div>
                <div class="info-content">{}</div>
            </div>
            """.format(group_name), unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">🎯 직급</div>
                <div class="info-content">{}</div>
            </div>
            """.format(rank), unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">👤 이름</div>
                <div class="info-content">{}</div>
            </div>
            """.format(user_name), unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div class="user-info-card">
                <div class="info-header">📧 이메일</div>
                <div class="info-content">{}</div>
            </div>
            """.format(user_email), unsafe_allow_html=True)

        # 구분선 추가
        st.markdown("---")
        
        # 활동 통계 섹션
        st.markdown("### 📊 활동 통계")
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            st.info(f"✍️ 작성한 리뷰: {written_reviews}건")
        with stat_col2:
            st.info(f"📥 받은 리뷰: {received_reviews}건")

    # 📌 리뷰 작성 / 리뷰 결과 페이지
    elif st.session_state.user_tab == "write":
        user_write_feedback()
    elif st.session_state.user_tab == "my_feedback":
        user_view_my_feedback()

    # st.sidebar.title("사용자 메뉴")
    # if st.sidebar.button("✍ 리뷰 작성"):
    #     st.session_state.user_tab = "write"
    # if st.sidebar.button("📋 리뷰 결과"):
    #     st.session_state.user_tab = "my_feedback"ㄱ

    # st.sidebar.markdown("---")
    # if st.sidebar.button("로그아웃"):
    #     do_logout()
    #     return

def do_logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.page = "login"
    st.rerun()

if __name__ == "__main__":
    main()