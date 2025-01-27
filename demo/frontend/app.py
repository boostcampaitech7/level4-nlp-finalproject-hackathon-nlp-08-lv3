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
    else:
        st.session_state.page = "login"
        st.stop()

def admin_page():
    st.subheader(f"관리자 페이지 - {st.session_state.name}님")

    st.sidebar.title("관리자 메뉴")
    if "admin_tab" not in st.session_state:
        st.session_state.admin_tab = "questions"

    if st.sidebar.button("⚙ 리뷰 템플릿 관리"):
        st.session_state.admin_tab = "questions"
    if st.sidebar.button("🔍 리뷰 결과 분석"):
        st.session_state.admin_tab = "feedback"
### 그룹 수정 시작
    if st.sidebar.button("👥 부서 관리"):
        st.session_state.admin_tab = "groups"
### 그룹 수정 끝

    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        do_logout()
        return

    if st.session_state.admin_tab == "questions":
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
    if response.status_code == 200 and response.json().get("success"):
        users = response.json()["users"]
        current_user = next((user for user in users if user["username"] == st.session_state.username), None)
        
        if current_user:
            group_name = current_user.get("group_name", "소속 없음")
            rank = current_user.get("rank", "")
            st.subheader(f"사용자 페이지 - {group_name} {rank} {st.session_state.name}님")
        else:
            st.subheader(f"사용자 페이지 - {st.session_state.name}님")
    else:
        st.subheader(f"사용자 페이지 - {st.session_state.name}님")

    if "user_tab" not in st.session_state:
        st.session_state.user_tab = "write"

    st.sidebar.title("사용자 메뉴")
    if st.sidebar.button("✍ 리뷰 작성"):
        st.session_state.user_tab = "write"
    if st.sidebar.button("📋 리뷰 결과"):
        st.session_state.user_tab = "my_feedback"

    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        do_logout()
        return

    if st.session_state.user_tab == "write":
        user_write_feedback()
    elif st.session_state.user_tab == "my_feedback":
        user_view_my_feedback()

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