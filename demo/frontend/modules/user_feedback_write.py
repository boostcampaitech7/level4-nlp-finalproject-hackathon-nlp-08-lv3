import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://localhost:5000/api"

def user_write_feedback():
    st.write("## 리뷰 작성")

    # 피드백 기간 확인
    resp = requests.get(f"{API_BASE_URL}/deadline")
    if resp.status_code == 200 and resp.json().get("success"):
        start_date = resp.json().get("start_date")
        deadline = resp.json().get("deadline")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not start_date or not deadline:
            st.warning("피드백 기간이 설정되지 않았습니다. 관리자에게 문의하세요.")
            return
        
        if current_time < start_date:
            st.warning("아직 피드백 기간 전입니다.")
            return
            
        if current_time > deadline:
            st.warning("피드백 기간이 종료되었습니다.")
            return

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

    # keyword 별로 질문 나누기
    keyword_map = {}
    for q in questions:
        keyword = q.get("keyword", "기타")
        if keyword not in keyword_map:
            keyword_map[keyword] = []
        keyword_map[keyword].append(q)

    answers = {}

    for keyword, qs in keyword_map.items():
        st.markdown(f"""
            <div style="background-color: #E8F6F3; padding: 20px; border-radius: 15px; margin: 25px 0; 
                        border-left: 5px solid #16A085; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="color: #16A085; margin: 0; font-size: 1.3em;">{keyword}</h3>
            </div>
        """, unsafe_allow_html=True)
        for q in qs:
            q_id = q["id"]
            q_text = q["question_text"]
            q_type = q["question_type"]
            q_opts = q["options"] or ""
            
            key_prefix = f"question_{q_id}"
            if q_type == "single_choice":
                opts = [opt.strip() for opt in q_opts.split(",")] if q_opts else []
                col1, col2 = st.columns([1.5, 3])
                with col1:
                    st.markdown(f"<p style='color: #666;'><strong>{q_text}</strong></p>", unsafe_allow_html=True)
                with col2:
                    chosen = st.radio("", opts, key=f"{key_prefix}_radio", horizontal=True, index=None)
                answers[q_id] = chosen
                st.markdown("---")
            else:
                st.markdown(f"<p style='color: #666;'><strong>{q_text}</strong></p>", unsafe_allow_html=True)
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
            error_msg = response.json().get("message", "리뷰 제출에 실패했습니다.")
            st.error(error_msg)