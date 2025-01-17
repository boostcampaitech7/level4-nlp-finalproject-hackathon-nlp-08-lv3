import streamlit as st
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY")
API_BASE_URL = "http://localhost:5000/api"

def account_created_page():
    st.title("계정 생성이 완료되었습니다.")
    st.write("2초 후에 로그인 페이지로 이동합니다...")
    time.sleep(2)
    st.session_state.account_created = False
    st.session_state.page = "login"
    st.rerun()

def create_account_page():
    st.title("새 계정 생성 페이지")

    new_username = st.text_input("새 계정 아이디(중복 불가)", key="new_username")
    new_name = st.text_input("이름(실명)", key="new_name")
    new_password = st.text_input("새 계정 비밀번호", type="password", key="new_password")
    new_role = st.selectbox("새 계정 역할", ["admin", "user"], key="new_role_select")

    admin_key_input = ""
    if new_role == "admin":
        admin_key_input = st.text_input("관리자 key 입력", type="password", key="admin_key_input")

    if st.button("계정 생성", key="create_account_btn"):
        if new_role == "admin":
            if admin_key_input != ADMIN_KEY:
                st.error("관리자 key가 올바르지 않습니다.")
                return
        payload = {
            "username": new_username,
            "name": new_name,
            "password": new_password,
            "role": new_role
        }
        resp = requests.post(f"{API_BASE_URL}/create_account", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data["success"]:
                st.success(data["message"])
                st.session_state.account_created = True
                st.rerun()
            else:
                st.error(data["message"])
        else:
            st.error("계정 생성 API 오류")

    if st.button("로그인 페이지로 돌아가기", key="return_to_login"):
        st.session_state.page = "login"
        st.rerun()
