import streamlit as st
import requests
import pandas as pd
import subprocess  # 추가된 부분
import os

API_BASE_URL = "http://localhost:5000/api"

def admin_view_feedback():
    st.write("## 리뷰 결과 분석")

    r = requests.get(f"{API_BASE_URL}/users")
    if r.status_code == 200 and r.json().get("success"):
        all_users = r.json()["users"]
        filtered_users = [u for u in all_users if u["role"] == "user"]
        if not filtered_users:
            st.info("일반 사용자 계정이 없습니다.")
            return
        name_map = {u["name"]: u["username"] for u in filtered_users}
        
        # 피드백 완료 여부 확인
        feedback_matrix = []
        for from_user in filtered_users:
            row = []
            for to_user in filtered_users:
                if from_user["username"] == to_user["username"]:
                    row.append("-")
                else:
                    response = requests.get(f"{API_BASE_URL}/feedback/check", params={"from_username": from_user["username"], "to_username": to_user["username"]})
                    if response.status_code == 200 and response.json().get("success"):
                        if response.json().get("already_submitted"):
                            row.append("✔️")
                        else:
                            row.append("❌")
                    else:
                        row.append("❌")
            feedback_matrix.append(row)
        
        df_status = pd.DataFrame(feedback_matrix, columns=[u["name"] for u in filtered_users], index=[u["name"] for u in filtered_users])
        st.table(df_status)
        
        # PDF 생성 제어 상태 초기화
        if "pdf_generated" not in st.session_state:
            st.session_state.pdf_generated = False

        # PDF 생성 버튼
        if not st.session_state.pdf_generated:
            if st.button("PDF 생성 시작"):
                backend_dir = os.path.join(os.path.dirname(__file__), "../../backend")
                subprocess.run(["python", os.path.join(backend_dir, "pdf_db.py")])
                subprocess.run(["python", os.path.join(backend_dir, "pdf.py")])
                st.session_state.pdf_generated = True
                st.success("PDF 생성이 완료되었습니다.")
        else:
            st.warning("PDF가 이미 생성되었습니다.")

        # PDF가 생성된 경우에만 결과 조회 옵션 표시
        if st.session_state.pdf_generated:
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
        else:
            st.info("PDF를 생성한 후에 결과를 조회할 수 있습니다.")
