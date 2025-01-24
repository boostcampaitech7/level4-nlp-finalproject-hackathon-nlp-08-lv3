import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:5000/api"

def user_view_my_feedback():
    st.write("## 리뷰 결과")

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
            st.info("아직 받은 리뷰가 없습니다.")
    else:
        st.error("리뷰 조회 API 오류")