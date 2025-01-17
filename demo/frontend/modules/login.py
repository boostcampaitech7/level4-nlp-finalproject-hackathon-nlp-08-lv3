import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY")
API_BASE_URL = "http://localhost:5000/api"

def login_page():
    st.title("동료 피드백 플랫폼 (로그인)")

    tab_admin, tab_user = st.tabs(["관리자 로그인", "사용자 로그인"])

    with tab_admin:
        admin_username = st.text_input("관리자 아이디", key="admin_username_input")
        admin_password = st.text_input("비밀번호", type="password", key="admin_password_input")
        if st.button("관리자 로그인", key="admin_login_btn"):
            payload = {"username": admin_username, "password": admin_password}
            resp = requests.post(f"{API_BASE_URL}/login", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("role") == "admin":
                    st.session_state.logged_in = True
                    st.session_state.role = data["role"]
                    st.session_state.user_id = data["user_id"]
                    st.session_state.username = admin_username
                    st.session_state.name = data["name"]
                    st.success("관리자 로그인 성공")
                    st.rerun()
                else:
                    st.error("관리자 로그인 실패")
            else:
                st.error("로그인 API 오류")

    with tab_user:
        user_username = st.text_input("사용자 아이디", key="user_username_input")
        user_password = st.text_input("비밀번호", type="password", key="user_password_input")
        if st.button("사용자 로그인", key="user_login_btn"):
            payload = {"username": user_username, "password": user_password}
            resp = requests.post(f"{API_BASE_URL}/login", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("role") == "user":
                    st.session_state.logged_in = True
                    st.session_state.role = data["role"]
                    st.session_state.user_id = data["user_id"]
                    st.session_state.username = user_username
                    st.session_state.name = data["name"]
                    st.success("사용자 로그인 성공")
                    st.rerun()
                else:
                    st.error("사용자 로그인 실패")
            else:
                st.error("로그인 API 오류")

    st.write("---")
    if st.button("계정 생성"):
        st.session_state.page = "create_account"
        st.rerun()
