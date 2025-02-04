import streamlit as st
import sqlite3
import os
import ast  # 문자열 리스트를 실제 리스트로 변환
import base64  # 버튼 스타일 적용을 위한 base64 변환

def user_view_my_feedback():
    st.subheader("📋 리뷰 결과")

    my_uname = st.session_state.get("username", None)
    pdf_path = os.path.join(os.path.dirname(__file__), f"../../backend/pdf/{my_uname}.pdf")

    # 🔹 PDF 파일이 존재하는지 확인
    if os.path.exists(pdf_path):  
        # PDF 파일을 읽고 base64로 인코딩 (HTML 버튼 스타일링 적용)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode()

        # 📌 오른쪽 정렬된 다운로드 버튼
        button_html = f"""
        <div style="display: flex; justify-content: flex-end;">
            <a href="data:application/pdf;base64,{pdf_base64}" download="{my_uname}.pdf">
                <button style="
                    background-color: #4CAF50;
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 5px;
                ">
                    📄 PDF 다운로드
                </button>
            </a>
        </div>
        """
        st.markdown(button_html, unsafe_allow_html=True)

    else:
        st.error("PDF 생성에 실패했습니다. 다시 시도해주세요.")
    
    try:
        RESULT_DB_PATH = os.path.join(os.path.dirname(__file__), "../../backend/db/result.db")
        FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "../../backend/db/feedback.db")
    except Exception as e:
        st.error(f"❌ 경로 설정 중 오류 발생: {e}")
        return

    # SQLite 연결
    with sqlite3.connect(RESULT_DB_PATH) as conn_result:
        conn_result.row_factory = sqlite3.Row
        cursor_result = conn_result.cursor()

        with sqlite3.connect(FEEDBACK_DB_PATH) as conn_feedback:
            conn_feedback.row_factory = sqlite3.Row
            cursor_feedback = conn_feedback.cursor()

            # 🔹 사용자별 피드백 데이터 가져오기 (모든 칼럼 동적 로딩)
            query = "SELECT * FROM subjective WHERE to_username = ?"
            cursor_result.execute(query, (my_uname,))
            feedback_row = cursor_result.fetchone() # 피드백 칼럼 목록 확인

            if not feedback_row:
                st.warning("❗ 피드백 데이터가 없습니다.")
                return

            # 🔹 feedback_questions 테이블에서 keyword 가져오기
            cursor_feedback.execute("SELECT DISTINCT keyword FROM feedback_questions")
            keywords = [row["keyword"] for row in cursor_feedback.fetchall()]

            # 🔹 질문 ID 매핑 (keyword 기반 자동 매핑)
            categories = {}
            question_texts = {}
            for keyword in keywords:
                cursor_feedback.execute("SELECT id, question_text FROM feedback_questions WHERE keyword = ?", (keyword,))
                question_data = cursor_feedback.fetchall()
                question_ids = [f"q_{row['id']}" for row in question_data]
                categories[f"📊 {keyword}"] = question_ids  # 카테고리명 동적 생성
                for row in question_data:
                    question_texts[f"q_{row['id']}"] = row['question_text']

    # 🔹 피드백 내용만 표시
    st.subheader("💬 상세 피드백")

    # CSS 스타일 적용
    gray_box_style = """
        <style>
            .gray-box {
                background-color: #f8f9fa; /* 연한 회색 */
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #d6d6d6;
            }
            .gray-box p {
                font-size: 16px;
                color: #333333;
            }
            .gray-box strong {
                color: #333333;
            }
            .question-box {
                background-color: #f8f9fa; /* 흰색 */
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid #d6d6d6;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .question-box p {
                font-size: 16px;
                color: #333333;
            }
            .question-box strong {
                color: #333333;
            }
        </style>
    """
    st.markdown(gray_box_style, unsafe_allow_html=True)

    # 피드백 데이터 출력
    for category, question_keys in categories.items():
        st.subheader(category)

        feedback_list = []
        for idx, key in enumerate(question_keys, start=1):
            if key in feedback_row.keys():  # 존재하는 키인지 확인
                raw_data = feedback_row[key]
                if raw_data:
                    try:
                        # 🔹 문자열 형태의 리스트를 실제 리스트로 변환
                        feedback_items = ast.literal_eval(raw_data) if isinstance(raw_data, str) else raw_data
                        if isinstance(feedback_items, list):
                            formatted_feedback = "<br><br>".join([f"• {item}" for item in feedback_items])
                        else:
                            formatted_feedback = f"• {feedback_items}"

                        question_text = question_texts.get(key, "질문 텍스트 없음")
                        feedback_list.append(f"📌 {question_text} \n\n{formatted_feedback}")
                        # 질문별 박스 스타일 적용
                        st.markdown(
                            f"""
                            <div class="question-box">
                                <strong>📌 {question_text}</strong>
                                <br><br>
                                {formatted_feedback}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                    except Exception as e:
                        st.error(f"❌ 데이터 변환 오류: {e}")

        if not feedback_list:
            st.warning("🚨 해당 카테고리에 대한 피드백이 없습니다.")

        st.write("---")  # 카테고리별 구분선 추가