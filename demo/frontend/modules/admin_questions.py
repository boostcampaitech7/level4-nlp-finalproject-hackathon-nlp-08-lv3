import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:5000/api"

def admin_manage_questions():
    st.write("## 동료 피드백 질문 관리")

    resp = requests.get(f"{API_BASE_URL}/questions")
    if resp.status_code == 200 and resp.json().get("success"):
        questions = resp.json()["questions"]

        type_map = {
            "single_choice": "객관식(단일)",
            "multi_choice": "객관식(복수)",
            "long_answer": "주관식"
        }

        for q in questions:
            q_id = q["id"]
            q_kw = q["keyword"] or ""
            q_txt = q["question_text"]
            q_type_db = q["question_type"]
            q_type_kor = type_map.get(q_type_db, q_type_db)

            if q_type_db == "long_answer":
                q_opts = None
            else:
                q_opts = q["options"] or ""

            col_info, col_edit, col_delete = st.columns([6, 0.5, 0.5])
            
            with col_info:
                st.write(f"**질문 ID {q_id}**")
                st.write(f"**Keyword**: {q_kw}")
                st.write(f"**질문 내용**: {q_txt}")
                st.write(f"**유형**: {q_type_kor}")
                if q_opts:
                    st.write(f"**옵션**: {q_opts}")

            with col_edit:
                if st.button("수정", key=f"edit_{q_id}"):
                    st.session_state.page = "question_edit"
                    st.session_state.edit_question_id = q_id
                    st.rerun()

            with col_delete:
                if st.button("삭제", key=f"delete_{q_id}"):
                    resp_del = requests.delete(f"{API_BASE_URL}/questions/{q_id}")
                    if resp_del.status_code == 200 and resp_del.json().get("success"):
                        st.success("질문이 성공적으로 삭제되었습니다.")
                    else:
                        st.error("질문 삭제 실패")
                    st.rerun()

            st.divider()

        if st.button("질문 추가", key="add_question_button"):
            st.session_state.page = "question_add"
            st.rerun()
        
        if st.button("PDF로 질문 추가", key="add_question_from_pdf_button"):
            st.session_state.page = "question_add_from_pdf"
            st.rerun()
    else:
        st.error("질문 목록 조회 실패")

def preview_questions():
    st.write("## 미리보기: 동료 피드백 작성 화면")

    r_q = requests.get(f"{API_BASE_URL}/questions")
    if r_q.status_code == 200 and r_q.json().get("success"):
        questions = r_q.json()["questions"]
    else:
        st.error("질문 목록 불러오기 실패 (미리보기)")
        return

    for q in questions:
        q_id = q["id"]
        q_text = q["question_text"]
        q_type = q["question_type"]
        q_opts = q["options"] or ""

        st.write(f"**Q{q_id}**: {q_text}")
        key_prefix = f"preview_{q_id}"
        if q_type == "single_choice":
            opts = [opt.strip() for opt in q_opts.split(",")] if q_opts else []
            st.radio("(객관식 단일) 선택", opts, key=f"{key_prefix}_radio")
        elif q_type == "multi_choice":
            opts = [opt.strip() for opt in q_opts.split(",")] if q_opts else []
            st.multiselect("(객관식 복수) 선택", opts, key=f"{key_prefix}_multi")
        elif q_type == "long_answer":
            st.text_area("(장문형) 답변 입력 예시", key=f"{key_prefix}_text")

    st.info("이 화면은 미리보기 전용입니다. 실제 제출 기능은 없습니다.")

def question_add_page():
    st.title("질문 추가")

    new_kw = st.text_input("keyword")
    new_text = st.text_input("질문")
    new_type = st.selectbox("질문 유형", ["single_choice","multi_choice","long_answer"])

    if new_type == "long_answer":
        new_opts = ""
    else:
        new_opts = st.text_input("옵션 (쉼표로 구분)")

    if st.button("추가"):
        payload = {
            "keyword": new_kw,
            "question_text": new_text,
            "question_type": new_type,
            "options": new_opts.strip() if new_opts.strip() else None
        }
        r2 = requests.post(f"{API_BASE_URL}/questions", json=payload)
        if r2.status_code == 200 and r2.json().get("success"):
            st.success("새로운 질문이 등록되었습니다.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("질문 등록 API 실패")

    if st.button("취소"):
        st.session_state.page = "login"
        st.rerun()

def question_edit_page(question_id):
    st.title("질문 수정")

    resp = requests.get(f"{API_BASE_URL}/questions/{question_id}")
    if resp.status_code == 200 and resp.json().get("success"):
        question = resp.json()["question"]

        edit_keyword = st.text_input("Keyword", value=question["keyword"] or "")
        edit_text = st.text_input("질문", value=question["question_text"])
        old_type = question["question_type"]

        edit_type = st.selectbox(
            "질문 유형",
            ["single_choice", "multi_choice", "long_answer"],
            index=["single_choice", "multi_choice", "long_answer"].index(old_type)
            if old_type in ["single_choice", "multi_choice", "long_answer"] else 0
        )

        if edit_type == "long_answer":
            edit_opts = ""
        else:
            edit_opts = st.text_input("옵션", value=question["options"] or "")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("수정 완료"):
                payload = {
                    "keyword": edit_keyword,
                    "question_text": edit_text,
                    "question_type": edit_type,
                    "options": edit_opts if edit_opts.strip() else None
                }
                update_resp = requests.put(f"{API_BASE_URL}/questions/{question_id}", json=payload)
                if update_resp.status_code == 200 and update_resp.json().get("success"):
                    st.success("질문이 성공적으로 수정되었습니다.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("질문 수정 실패")
        with col2:
            if st.button("취소"):
                st.session_state.page = "login"
                st.rerun()
    else:
        st.error("질문 정보를 불러올 수 없습니다.")
