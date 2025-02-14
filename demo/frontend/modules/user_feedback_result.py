import ast  # 문자열 리스트를 실제 리스트로 변환
import base64  # 버튼 스타일 적용을 위한 base64 변환
import os
import sqlite3
import streamlit as st


def user_view_my_feedback():
    st.write("## 📋 리뷰 결과")

    my_uname = st.session_state.get("username", None)
    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        f"pdf/{my_uname}.pdf",
    )

    # 🔹 PDF 파일이 존재하는지 확인
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode()

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

        if not os.path.exists(RESULT_DB_PATH):
            st.warning("❗ 피드백이 집계되지 않았습니다.")
            return

        with sqlite3.connect(RESULT_DB_PATH) as conn_result, sqlite3.connect(FEEDBACK_DB_PATH) as conn_feedback:
            conn_result.row_factory = sqlite3.Row
            conn_feedback.row_factory = sqlite3.Row
            cursor_result = conn_result.cursor()
            cursor_feedback = conn_feedback.cursor()

            # 🔹 사용자별 피드백 데이터 가져오기
            cursor_result.execute("SELECT * FROM subjective WHERE to_username = ?", (my_uname,))
            feedback_row = cursor_result.fetchone()

            if not feedback_row:
                st.warning("❗ 피드백 데이터가 없습니다.")
                return

            # 🔹 feedback_questions 테이블에서 keyword 가져오기
            cursor_feedback.execute("SELECT DISTINCT keyword FROM feedback_questions")
            keywords = [row["keyword"] for row in cursor_feedback.fetchall()]

            # 🔹 질문 ID 매핑
            categories = {}
            question_texts = {}
            for keyword in keywords:
                cursor_feedback.execute(
                    "SELECT id, question_text FROM feedback_questions WHERE keyword = ?",
                    (keyword,),
                )
                question_data = cursor_feedback.fetchall()
                question_ids = [f"q_{row['id']}" for row in question_data]
                categories[f"📊 {keyword}"] = question_ids
                for row in question_data:
                    question_texts[f"q_{row['id']}"] = row["question_text"]

    except Exception as e:
        st.error(f"❌ 데이터베이스 오류 발생: {e}")
        return

    # 🔹 피드백 내용 출력
    st.subheader("💬 상세 피드백")

    # CSS 스타일 적용
    gray_box_style = """
        <style>
            .gray-box {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border: 1px solid #d6d6d6;
            }
            .question-box {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                border: 1px solid #d6d6d6;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
        </style>
    """
    st.markdown(gray_box_style, unsafe_allow_html=True)

    for category, question_keys in categories.items():
        st.subheader(category)

        feedback_list = []
        for key in question_keys:
            if key in feedback_row.keys():
                raw_data = feedback_row[key]
                if raw_data:
                    try:
                        feedback_items = ast.literal_eval(raw_data) if isinstance(raw_data, str) else raw_data
                        formatted_feedback = "<br><br>".join(f"• {item}" for item in feedback_items) if isinstance(feedback_items, list) else f"• {feedback_items}"
                        question_text = question_texts.get(key, "질문 텍스트 없음")

                        st.markdown(
                            f"""
                            <div class="question-box">
                                <strong>📌 {question_text}</strong>
                                <br><br>
                                {formatted_feedback}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    except Exception as e:
                        st.error(f"❌ 데이터 변환 오류: {e}")

        if not feedback_list:
            st.warning("🚨 해당 카테고리에 대한 피드백이 없습니다.")

        st.write("---")  # 카테고리별 구분선 추가
