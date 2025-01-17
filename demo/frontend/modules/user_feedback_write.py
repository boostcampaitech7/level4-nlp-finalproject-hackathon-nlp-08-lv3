import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

def user_write_feedback():
    st.write("## 동료 피드백 작성")

    r_q = requests.get(f"{API_BASE_URL}/questions")
    if r_q.status_code == 200 and r_q.json().get("success"):
        questions = r_q.json()["questions"]
    else:
        st.error("질문 목록 불러오기 실패")
        return

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
        elif q_type == "long_answer":
            long_ans = st.text_area("답변 입력 (장문형)", key=f"{key_prefix}_text")
            answers[q_id] = long_ans

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
