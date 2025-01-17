import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

def question_add_from_pdf_page():
    st.title("파일로 질문 추가")

    uploaded_file = st.file_uploader("파일 업로드", type=["pdf", "jpeg", "png", "bmp", "tiff", "heic", "docx", "xlsx", "pptx"])

    if uploaded_file is not None:
        if uploaded_file.size > 50 * 1024 * 1024:
            st.error("파일 크기는 50MB를 초과할 수 없습니다.")
        else:
            files = {
                "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
            }
            response = requests.post(f"{API_BASE_URL}/upload_file", files=files)

            if response.status_code == 200 and response.json().get("success"):
                st.success("파일에서 질문을 성공적으로 추가했습니다.")
            else:
                st.error("파일 업로드 실패")

    if st.button("취소"):
        st.session_state.page = "login"
        st.rerun()
