import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

def user_write_feedback():
    st.write("## 리뷰 작성")

    r_u = requests.get(f"{API_BASE_URL}/users")
    if r_u.status_code == 200 and r_u.json().get("success"):
        all_users = r_u.json()["users"]
        curr_group = [u["group_id"] for u in all_users if u["username"] == st.session_state.username]
        filtered = [u for u in all_users if u["role"] == "user" and u["username"] != st.session_state.username and u['group_id'] == curr_group[0]]
        if not filtered:
            st.info("리뷰를 작성할 다른 사용자(일반 사용자)가 없습니다.")
            return
        name_map = {u["name"]: u["username"] for u in filtered}
        sel_name = st.selectbox("리뷰 대상 사용자", list(name_map.keys()))
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
            st.warning("이미 리뷰를 작성한 사용자입니다.")
            return
    else:
        st.error("리뷰 확인 API 오류")
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
            st.success("리뷰 제출 완료!")
        else:
            st.error("리뷰 제출에 실패했습니다.")