import streamlit as st
import requests
import os
from dotenv import load_dotenv
import base64

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

ADMIN_KEY = os.getenv("ADMIN_KEY")
API_BASE_URL = "http://localhost:5000/api"

def login_page():
    # 중앙 정렬 CSS 스타일 추가
    st.markdown(
        """
        <style>
        .center-image {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .centered-box {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .center-text {
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # 상단 로고 중앙 정렬
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    image_dir = os.path.join(base_dir, "images")
    file_path = os.path.join(image_dir, "logo.png")
    if os.path.exists(file_path):
        st.markdown(
            f"""
            <div class="center-image">
                <img src="data:image/png;base64,{get_base64_image(file_path)}" width="200" />
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.error(f"이미지 파일이 존재하지 않습니다: {file_path}")

    # 로그인 UI
    col1, col2, col3 = st.columns([1, 2, 1])  # 가운데 정렬
    with col2:
        # 로그인 제목을 중앙 정렬로 표시
        st.markdown('<div class="center-text"></div>', unsafe_allow_html=True)

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
                elif resp.status_code == 401:  # 인증 실패 관련 오류 처리
                    error_message = resp.json().get("error", "")
                    if error_message == "invalid username":
                        st.error("아이디 오류: 존재하지 않는 아이디입니다.")
                    elif error_message == "invalid password":
                        st.error("비밀번호 오류: 비밀번호가 틀렸습니다.")
                    else:
                        st.error("로그인 실패: 인증 오류가 발생했습니다.")
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
                elif resp.status_code == 401:  # 인증 실패 관련 오류 처리
                    error_message = resp.json().get("error", "")
                    if error_message == "invalid username":
                        st.error("아이디 오류: 존재하지 않는 아이디입니다.")
                    elif error_message == "invalid password":
                        st.error("비밀번호 오류: 비밀번호가 틀렸습니다.")
                    else:
                        st.error("로그인 실패: 인증 오류가 발생했습니다.")
                else:
                    st.error("로그인 API 오류")

        st.write("---")
        if st.button("계정 생성"):
            st.session_state.page = "create_account"
            st.rerun()

# Helper function to encode image to Base64
def get_base64_image(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
