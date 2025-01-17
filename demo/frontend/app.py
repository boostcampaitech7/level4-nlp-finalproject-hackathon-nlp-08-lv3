import streamlit as st
import time
from dotenv import load_dotenv

load_dotenv()

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

from modules.login import login_page
from modules.account import create_account_page, account_created_page
from modules.admin_questions import admin_manage_questions, preview_questions, question_add_page, question_edit_page
from modules.admin_feedback import admin_view_feedback
from modules.user_feedback_write import user_write_feedback
from modules.user_feedback_result import user_view_my_feedback
from modules.upload_files import question_add_from_pdf_page

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

    if st.sidebar.button("동료 피드백 질문 관리"):
        st.session_state.admin_tab = "questions"
    if st.sidebar.button("동료 피드백 결과 조회"):
        st.session_state.admin_tab = "feedback"

    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        do_logout()
        return

    if st.session_state.admin_tab == "questions":
        tab_manage, tab_preview = st.tabs(["편집", "미리보기"])
        with tab_manage:
            admin_manage_questions()
        with tab_preview:
            preview_questions()
    elif st.session_state.admin_tab == "feedback":
        admin_view_feedback()

def user_page():
    st.subheader(f"사용자 페이지 - {st.session_state.name}님")

    if "user_tab" not in st.session_state:
        st.session_state.user_tab = "write"

    st.sidebar.title("사용자 메뉴")
    if st.sidebar.button("동료 피드백 작성"):
        st.session_state.user_tab = "write"
    if st.sidebar.button("내 동료 피드백 결과 조회"):
        st.session_state.user_tab = "my_feedback"

    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        do_logout()
        return

    if st.session_state.user_tab == "write":
        user_write_feedback()
    elif st.session_state.user_tab == "my_feedback":
        user_view_my_feedback()

def user_write_feedback():
    st.write("## 동료 피드백 작성")

    r_u = requests.get(f"{API_BASE_URL}/users")
    if r_u.status_code == 200 and r_u.json().get("success"):
        all_users = r_u.json()["users"]
        filtered = [u for u in all_users if u["role"] == "user" and u["username"] != st.session_state.username]
        if not filtered:
            st.info("피드백을 보낼 다른 사용자(일반 사용자)가 없습니다.")
            return
        name_map = {u["name"]: u["username"] for u in filtered}
        sel_name = st.selectbox("피드백 대상 사용자", list(name_map.keys()))
        to_username = name_map[sel_name]
    else:
        st.error("사용자 목록 조회 실패")
        return

    # 이미 작성된 피드백인지 확인
    check_resp = requests.get(f"{API_BASE_URL}/feedback/check", params={
        "from_username": st.session_state.username,
        "to_username": to_username
    })
    if check_resp.status_code == 200 and check_resp.json().get("success"):
        if check_resp.json().get("already_submitted"):
            st.warning("이미 피드백을 작성한 사용자입니다.")
            return
    else:
        st.error("피드백 확인 API 오류")
        return
    
    # 질문 출력 및 답변 작성
    r_q = requests.get(f"{API_BASE_URL}/questions")
    if r_q.status_code == 200 and r_q.json().get("success"):
        questions = r_q.json()["questions"]
    else:
        st.error("질문 목록 불러오기 실패")
        return
    
    answers = {}
    for q in questions:
        q_id = q["id"]
        q_text = q["question_text"]
        q_type = q["question_type"]
        q_opts = q["options"] or ""
        st.write(f"**Q{q_id}**: {q_text}")

        key_prefix = f"question_{q_id}"
        if q_type == "single_choice":
            opts = [opt.strip() for opt in q_opts.split(",")] if q_opts else []
            chosen = st.radio("선택", opts, key=f"{key_prefix}_radio")
            answers[q_id] = chosen
        elif q_type == "multi_choice":
            opts = [opt.strip() for opt in q_opts.split(",")] if q_opts else []
            chosen = st.multiselect("선택(복수)", opts, key=f"{key_prefix}_multi")
            answers[q_id] = ", ".join(chosen)
        else:
            short_ans = st.text_input("답변 입력", key=f"{key_prefix}_text")
            answers[q_id] = short_ans

    if st.button("제출"):
        from_username = st.session_state.username

        # 작성하지 않은 항목 확인
        unanswered_questions = [q_id for q_id, ans in answers.items() if not ans]
        if unanswered_questions:
            st.error(f"작성하지 않은 항목이 있습니다: {', '.join([str(q) for q in unanswered_questions])}")
            return

        # 모든 답변을 한 번에 서버로 전송
        payload = [
            {
                "question_id": question_id,
                "from_username": from_username,
                "to_username": to_username,
                "answer_content": ans
            }
            for question_id, ans in answers.items()
        ]

        response = requests.post(f"{API_BASE_URL}/feedback/bulk", json=payload)
        if response.status_code == 200 and response.json().get("success"):
            st.success("피드백 제출 완료!")
        else:
            st.error("피드백 제출에 실패했습니다.")

def user_view_my_feedback():
    st.write("## 내가 받은 피드백 결과 조회")

    my_uname = st.session_state.username
    params = {"username": my_uname}
    r = requests.get(f"{API_BASE_URL}/feedback/my", params=params)
    if r.status_code == 200 and r.json().get("success"):
        feedbacks = r.json()["feedbacks"]
        if feedbacks:
            sorted_fb = sorted(feedbacks, key=lambda x: x["question_id"])
            rows = []
            for fb in sorted_fb:
                q_id = fb["question_id"]
                from_u = fb["from_username"]
                ans = fb["answer_content"]
                rows.append([q_id, from_u, ans])
            df_fb = pd.DataFrame(rows, columns=["질문ID","작성자","답변"])
            st.table(df_fb)
        else:
            st.info("아직 받은 피드백이 없습니다.")
    else:
        st.error("피드백 조회 API 오류")

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