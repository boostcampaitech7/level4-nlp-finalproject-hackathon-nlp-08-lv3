import streamlit as st
import requests
import os

API_BASE_URL = "http://localhost:5000/api"

def user_view_my_feedback():
    st.write("## 리뷰 결과")

    my_uname = st.session_state.username

    # 결과 요약 페이지 표시
    result_db_path = os.path.join(os.path.dirname(__file__), "../../backend/db/result.db")
    if os.path.exists(result_db_path):
        pdf_url = f"{API_BASE_URL}/summary/{my_uname}"
        pdf_display = f"""<iframe src="{pdf_url}" width="800" height="1200" style="border: none;"></iframe>"""
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.warning("결과를 현재 집계중입니다. 잠시 후 다시 시도해주세요.")