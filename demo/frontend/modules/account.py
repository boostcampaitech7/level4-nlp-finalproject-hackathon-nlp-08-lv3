import streamlit as st
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

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
    new_email = st.text_input("이메일", key="new_email")
    new_password = st.text_input("새 계정 비밀번호", type="password", key="new_password")
    new_role = st.selectbox("새 계정 역할", ["admin", "user"], key="new_role_select")

    # 부서 목록 가져오기
    if new_role == "user":
        response = requests.get(f"{API_BASE_URL}/groups")
        if response.status_code == 200:
            groups = response.json().get("groups", [])
            group_options = {group["group_name"]: group["id"] for group in groups}
        else:
            st.error("부서 목록을 가져오는 데 실패했습니다.")
            group_options = {}

        selected_group = st.selectbox("부서 선택", ["선택"] + list(group_options.keys()), key="new_group_select")
        selected_rank = st.selectbox("직급 선택", ["팀장", "팀원"], key="new_rank_select")

    admin_key_input = ""
    if new_role == "admin":
        admin_key_input = st.text_input("관리자 key 입력", type="password", key="admin_key_input")

    # 이메일 유효성 검사 함수
    def is_valid_email(email):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    if st.button("계정 생성", key="create_account_btn"):
        if not new_username:
            st.error("아이디를 입력해주세요.")
            return
        if not new_name:
            st.error("이름을 입력해주세요.")
            return
        if not new_email:
            st.error("이메일을 입력해주세요.")
            return
        if not is_valid_email(new_email):
            st.error("올바른 이메일 형식이 아닙니다.")
            return
        if not new_password:
            st.error("비밀번호를 입력해주세요.")
            return
        if not is_valid_email(new_email):
            st.error("올바른 이메일 형식이 아닙니다.")
            return

        if new_role == "user" and selected_group == "선택":
            st.error("부서를 선택해주세요.")
            return

        if new_role == "admin":
            if admin_key_input != ADMIN_KEY:
                st.error("관리자 key가 올바르지 않습니다.")
                return

        payload = {
            "username": new_username,
            "name": new_name,
            "email": new_email,
            "password": new_password,
            "role": new_role,
            "group_id": group_options[selected_group] if new_role == "user" else None,
            "rank": selected_rank if new_role == "user" else None
        }

        # 아이디 중복 확인
        username_resp = requests.get(f"{API_BASE_URL}/check_username", params={"username": new_username})
        if username_resp.status_code == 200:
            username_data = username_resp.json()
            if not username_data["available"]:
                st.error("이미 사용 중인 아이디입니다.")
                return
        else:
            st.error("아이디 중복 확인 중 오류가 발생했습니다.")
            return

        # 이메일 중복 확인
        email_resp = requests.get(f"{API_BASE_URL}/check_email", params={"email": new_email})
        if email_resp.status_code == 200:
            email_data = email_resp.json()
            if not email_data["available"]:
                st.error("이미 사용 중인 이메일입니다.")
                return
        else:
            st.error("이메일 중복 확인 중 오류가 발생했습니다.")
            return

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