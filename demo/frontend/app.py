from modules.login import login_page
from modules.account import create_account_page, account_created_page
from modules.admin_questions import admin_manage_questions, preview_questions, question_add_page, question_edit_page
from modules.admin_feedback import admin_view_feedback
from modules.user_feedback_write import user_write_feedback
from modules.user_feedback_result import user_view_my_feedback
from modules.upload_files import question_add_from_pdf_page
from modules.admin_group_manage import admin_manage_groups
from modules.mypage import admin_mypage, user_mypage
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
    st.set_page_config(layout="wide") # 동료피드백 플랫폼 제거

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
        
    if st.session_state.admin_tab == "mypage":
        admin_mypage() # 관리자 마이페이지
    elif st.session_state.admin_tab == "questions":
        admin_manage_questions()
    elif st.session_state.admin_tab == "feedback":
        admin_view_feedback()
    elif st.session_state.admin_tab == "groups":
        admin_manage_groups()

def user_page():
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

    if st.session_state.user_tab == "mypage":
        user_mypage() # 사용자 마이페이지
    elif st.session_state.user_tab == "write":
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