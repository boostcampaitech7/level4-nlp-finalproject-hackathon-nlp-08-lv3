import streamlit as st
from login import login_page
from admin.admin import admin_page, create_peer_feedback_form, view_feedback_form
from user import user_page

def main():
    if "page" not in st.session_state:
        st.session_state["page"] = "login"
        st.session_state["questions_with_options"] = []  # 질문과 항목 저장용 리스트
        st.session_state["max_selection"] = 1  # 최대 선택 가능한 항목 갯수

    if st.session_state["page"] == "login":
        login_page()

    elif st.session_state["page"] == "admin":
        admin_page()

    elif st.session_state["page"] == "user":
        user_page()

    elif st.session_state["page"] == "create_feedback_form":
        create_peer_feedback_form()

    elif st.session_state["page"] == "view_feedback_form":
        view_feedback_form()

if __name__ == "__main__":
    main()