import streamlit as st

USER_CREDENTIALS = {
    "admin": "password123", 
    "user": "userpass"
}

def login_page():
    st.title("Login")
    with st.form("login_form"):
        st.write("\n**아이디와 비밀번호를 입력하세요:**\n")
        username = st.text_input("아이디", value="admin")
        password = st.text_input("비밀번호", type="password", value="password123", key="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            if username == "admin":
                st.session_state["page"] = "admin"
            elif username == "user":
                st.session_state["page"] = "user"
        else:
            st.error("사용자 이름 또는 비밀번호가 잘못되었습니다.")
