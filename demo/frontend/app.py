import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:5000/api"

def main():
    st.set_page_config(page_title="동료 피드백 플랫폼", layout="wide")

    # 세션 상태
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

    # 페이지 라우팅
    if st.session_state.page == "login":
        if not st.session_state.logged_in:
            login_page()
        else:
            if st.session_state.role == "admin":
                admin_page()
            else:
                user_page()
    elif st.session_state.page == "create_account":
        create_account_page()
    else:
        st.session_state.page = "login"
        st.stop()

# ----------------------------------------------------------------------------
# 로그인 페이지
# ----------------------------------------------------------------------------
def login_page():
    st.title("동료 피드백 플랫폼 (로그인)")

    tab_admin, tab_user = st.tabs(["관리자 로그인", "사용자 로그인"])

    # 관리자 로그인
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
                    st.rerun()  # 대신 st.rerun()
                else:
                    st.error("관리자 로그인 실패")
            else:
                st.error("로그인 API 오류")

    # 사용자 로그인
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
        st.stop()

# ----------------------------------------------------------------------------
# 계정 생성 페이지
# ----------------------------------------------------------------------------
def create_account_page():
    st.title("새 계정 생성 페이지")

    new_username = st.text_input("새 계정 아이디(중복 불가)", key="new_username")
    new_name = st.text_input("이름(실명)", key="new_name")
    new_password = st.text_input("새 계정 비밀번호", type="password", key="new_password")
    new_role = st.selectbox("새 계정 역할", ["admin", "user"], key="new_role_select")

    if st.button("계정 생성", key="create_account_btn"):
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
            else:
                st.error(data["message"])
        else:
            st.error("계정 생성 API 오류")

    if st.button("로그인 페이지로 돌아가기", key="return_to_login"):
        st.session_state.page = "login"
        st.stop()

# ----------------------------------------------------------------------------
# 관리자 페이지
# ----------------------------------------------------------------------------
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
        admin_manage_questions()
    elif st.session_state.admin_tab == "feedback":
        admin_view_feedback()

def admin_manage_questions():
    st.write("## 동료 피드백 질문 관리")

    # 1) 질문 목록
    resp = requests.get(f"{API_BASE_URL}/questions")
    if resp.status_code == 200 and resp.json().get("success"):
        qs = resp.json()["questions"]
        type_map = {
            "single_choice": "객관식(단일 선택)",
            "multi_choice": "객관식(복수 선택)",
            "short_answer": "주관식",
        }
        rows = []
        for q in qs:
            q_id = q["id"]
            q_text = q["question_text"]
            q_type_kor = type_map.get(q["question_type"], q["question_type"])
            q_opts = q["options"]
            rows.append([q_id, q_text, q_type_kor, q_opts])

        df = pd.DataFrame(rows, columns=["ID", "질문", "유형", "옵션"])
        st.write("### 현재 등록된 질문들:")
        st.table(df)
    else:
        st.error("질문 목록 조회 실패")

    st.write("---")
    st.write("### 새로운 질문 등록하기")
    new_text = st.text_input("질문 내용")
    rev_map = {
        "객관식(단일 선택)": "single_choice",
        "객관식(복수 선택)": "multi_choice",
        "주관식": "short_answer",
    }
    q_label = st.selectbox("질문 유형", list(rev_map.keys()))
    new_type = rev_map[q_label]

    new_opts = ""
    if new_type in ["single_choice", "multi_choice"]:
        new_opts = st.text_input("옵션(쉼표로 구분)", placeholder="예: 매우 그렇다, 그렇다, 아니다")

    if st.button("질문 추가"):
        payload = {
            "question_text": new_text,
            "question_type": new_type,
            "options": new_opts.strip() if new_opts.strip() else None
        }
        r2 = requests.post(f"{API_BASE_URL}/questions", json=payload)
        if r2.status_code == 200 and r2.json()["success"]:
            st.success("새로운 질문이 등록되었습니다.")
            st.rerun()
        else:
            st.error("질문 등록 API 실패")


def admin_view_feedback():
    st.write("## 동료 피드백 결과 조회")
    st.write("사용자 이름을 선택하면 해당 사용자가 **받은** 피드백을 조회합니다.")

    r = requests.get(f"{API_BASE_URL}/users")
    if r.status_code == 200 and r.json()["success"]:
        user_list = r.json()["users"]
        if not user_list:
            st.info("등록된 사용자가 없습니다.")
            return

        # map: name -> username
        name_map = {u["name"]: u["username"] for u in user_list}
        sel_name = st.selectbox("조회할 사용자 이름", list(name_map.keys()))
        sel_username = name_map[sel_name]

        if st.button("결과 조회"):
            params = {"username": sel_username}
            fb_resp = requests.get(f"{API_BASE_URL}/feedback/user", params=params)
            if fb_resp.status_code == 200:
                data = fb_resp.json()
                if data.get("success"):
                    feedbacks = data["feedbacks"]
                    if feedbacks:
                        rows = []
                        for fb in feedbacks:
                            q_id = fb["question_id"]
                            from_u = fb["from_username"]
                            ans = fb["answer_content"]
                            created = fb["created_at"]
                            rows.append([q_id, from_u, ans, created])
                        df_fb = pd.DataFrame(rows, columns=["질문ID", "작성자", "답변", "작성일시"])
                        st.table(df_fb)
                    else:
                        st.info("해당 사용자가 받은 피드백이 없습니다.")
                else:
                    st.error("피드백 조회 실패: " + data.get("message", ""))
            else:
                st.error("피드백 조회 API 오류")
    else:
        st.error("사용자 목록 조회 실패")

# ----------------------------------------------------------------------------
# 사용자 페이지
# ----------------------------------------------------------------------------
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

    # 질문 목록
    r_q = requests.get(f"{API_BASE_URL}/questions")
    if r_q.status_code == 200 and r_q.json().get("success"):
        questions = r_q.json()["questions"]
    else:
        st.error("질문 목록 불러오기 실패")
        return

    # 사용자 목록 (role='user'), 자기 자신 제외
    r_users = requests.get(f"{API_BASE_URL}/users")
    if r_users.status_code == 200 and r_users.json().get("success"):
        all_users = r_users.json()["users"]
        filtered = [u for u in all_users if u["role"] == "user" and u["username"] != st.session_state.username]
        if not filtered:
            st.info("피드백을 보낼 다른 사용자(일반 사용자)가 없습니다.")
            return

        # 드롭다운: 이름 only, 실제 값: username
        name_map = {u["name"]: u["username"] for u in filtered}
        sel_name = st.selectbox("피드백 대상 사용자", list(name_map.keys()))
        to_username = name_map[sel_name]
    else:
        st.error("사용자 목록 조회 실패")
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
        for question_id, ans in answers.items():
            payload = {
                "question_id": question_id,
                "from_username": from_username,
                "to_username": to_username,
                "answer_content": ans
            }
            r_fb = requests.post(f"{API_BASE_URL}/feedback", json=payload)
            if r_fb.status_code == 200 and r_fb.json()["success"]:
                st.success(f"Q{question_id} 피드백 제출 완료")
            else:
                st.error(f"Q{question_id} 제출 실패")

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
                # created = fb["created_at"]
                rows.append([q_id, from_u, ans])
            df_fb = pd.DataFrame(rows, columns=["질문ID", "작성자", "답변"])
            st.table(df_fb)
        else:
            st.info("아직 받은 피드백이 없습니다.")
    else:
        st.error("피드백 조회 API 오류")

def do_logout():
    # 세션 초기화
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.page = "login"
    st.rerun()

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
