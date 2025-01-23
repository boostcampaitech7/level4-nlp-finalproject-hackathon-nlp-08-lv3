import streamlit as st
import requests
import pandas as pd

from modules.admin_feedback_summary import admin_feedback_summary

API_BASE_URL = "http://localhost:5000/api"

def admin_view_feedback():
    st.write("## 동료 피드백 결과 조회")

    r = requests.get(f"{API_BASE_URL}/users")
    if r.status_code == 200 and r.json().get("success"):
        all_users = r.json()["users"]
        filtered_users = [u for u in all_users if u["role"] == "user"]
        if not filtered_users:
            st.info("일반 사용자 계정이 없습니다.")
            return
        name_map = {u["name"]: u["username"] for u in filtered_users}
        sel_name = st.selectbox("조회할 사용자 이름", list(name_map.keys()))
        sel_username = name_map[sel_name]

    if st.button("결과 조회"):
        params = {"username": sel_username}
        fb = requests.get(f"{API_BASE_URL}/feedback/user", params=params)
        if fb.status_code == 200:
            data = fb.json()
            if data.get("success"):
                feedbacks = data["feedbacks"]
                if feedbacks:
                    # DataFrame 생성
                    rows = []
                    for fbb in feedbacks:
                        q_id = fbb["question_id"]
                        from_u = fbb["from_username"]
                        ans = fbb["answer_content"]
                        created = fbb["created_at"]
                        rows.append([q_id, from_u, ans, created])
                    df_fb = pd.DataFrame(rows, columns=["질문ID", "작성자", "답변", "작성일시"])

                    # 결과 요약 페이지 호출
                    admin_feedback_summary(df_fb)
                else:
                    st.info("해당 사용자가 받은 피드백이 없습니다.")
            else:
                st.error("피드백 조회 실패: " + data.get("message", ""))
        else:
            st.error("피드백 조회 API 오류")
