import streamlit as st
import requests
import json
from streamlit_tags import st_tags
import time  # 추가된 부분

API_BASE_URL = "http://localhost:5000/api"

def admin_manage_questions():
    st.write("## 동료 피드백 질문 관리")

    keywords = st_tags(
        label = '### 키워드 목록 작성',
        text='키워드를 입력하고 Enter를 누르세요',
        value=['업적','능력','리더십','협업','태도'],
        suggestions = [
    "창의성", "책임감", "효율성", "리더십", "협업", 
    "정확성", "적응력", "분석력", "열정", "신뢰성", 
    "시간관리", "혁신", "투명성", "결정력", "성실성", 
    "문제해결", "전문성", "의사소통", "동기부여", "감정지능", 
    "팀워크", "멘토링", "자기계발", "유연성", "갈등관리", 
    "목표달성", "학습", "공감", "창조성", "전략"
    ],
        maxtags=10,
        key='keywords'
    )
    
    if st.button("파일로 질문 추가", key="add_question_from_pdf_button"):
        st.session_state.page = "question_add_from_pdf"
        st.rerun()

    # 기존 질문 목록 표시
    resp = requests.get(f"{API_BASE_URL}/questions")
    if resp.status_code == 200 and resp.json().get("success"):
        questions = resp.json()["questions"]

        type_map = {
            "single_choice": "객관식(단일)",
            "multi_choice": "객관식(복수)",
            "long_answer": "주관식"
        }
        with st.expander("질문 추가하기", expanded=False):
            new_text = st.text_input("질문", key="new_text")
            new_kw = st.selectbox("keyword", options=keywords, key="new_kw")
            new_type = st.selectbox("질문 유형", 
                                  ["single_choice","multi_choice","long_answer"],
                                  key="new_type")

            if new_type != "long_answer":
                new_opts = st.text_input("옵션 (쉼표로 구분)", key="new_opts")
            else:
                new_opts = ""

            if st.button("추가하기"):
                payload = {
                    "question_text": new_text,
                    "keyword": new_kw,
                    "question_type": new_type,
                    "options": new_opts.strip() if new_opts.strip() else None
                }
                r2 = requests.post(f"{API_BASE_URL}/questions", json=payload)
                if r2.status_code == 200 and r2.json().get("success"):
                    st.success("성공적으로 질문이 추가되었습니다.")
                    time.sleep(2)  # 추가된 부분
                    st.rerun()
                else:
                    st.error("질문 추가에 실패했습니다.")
        for q in reversed(questions):
            q_id = q["id"]
            q_kw = q["keyword"] or ""
            q_txt = q["question_text"]
            q_type_db = q["question_type"]
            q_type_kor = type_map.get(q_type_db, q_type_db)

            if q_type_db == "long_answer":
                q_opts = None
            else:
                q_opts = q["options"] or ""

            # 수정 상태 확인
            is_editing = st.session_state.get(f"editing_{q_id}", False)

            # 수정 모드 UI
            if is_editing:
                # 수정 모드 UI
                st.write(f"**질문 ID**: {q_id}")
                
                # Check if selected keyword exists in keywords
                if q_kw not in keywords:
                    st.error(f"'{q_kw}' 는 키워드 목록에 없습니다. '{q_kw}' 를 키워드 목록에 추가해주세요.")
                else:
                    edit_kw = st.selectbox("Keyword", options=keywords, index=keywords.index(q_kw) if q_kw in keywords else 0, key=f"edit_kw_{q_id}")
                    edit_text = st.text_input("질문", value=q_txt, key=f"edit_text_{q_id}")
                    edit_type = st.selectbox(
                        "질문 유형",
                        ["single_choice", "multi_choice", "long_answer"],
                        index=["single_choice", "multi_choice", "long_answer"].index(q_type_db),
                        key=f"edit_type_{q_id}"
                    )

                    if edit_type == "long_answer":
                        edit_opts = ""
                    else:
                        edit_opts = st.text_input("옵션", value=q_opts, key=f"edit_opts_{q_id}")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("수정 완료", key=f"save_{q_id}"):
                            # Check if the keyword exists in the tags list
                            if edit_kw not in keywords:
                                st.error(f"'{edit_kw}' 는 키워드 목록에 없습니다. '(존재하지 않는 키워드)' 를 키워드 목록에 추가해주세요.")
                            else:
                                payload = {
                                    "keyword": edit_kw,
                                    "question_text": edit_text,
                                    "question_type": edit_type,
                                    "options": edit_opts if edit_opts.strip() else None
                                }
                                update_resp = requests.put(f"{API_BASE_URL}/questions/{q_id}", json=payload)
                                if update_resp.status_code == 200 and update_resp.json().get("success"):
                                    st.success("성공적으로 질문이 수정되었습니다.")
                                    time.sleep(2)
                                    st.session_state[f"editing_{q_id}"] = False
                                    st.rerun()
                                else:
                                    st.error("질문 수정에 실패했습니다.")
                    with col2:
                        if st.button("취소", key=f"cancel_{q_id}"):
                            st.session_state[f"editing_{q_id}"] = False
                            st.rerun()
                            
            else:
                # 일반 모드 UI
                col_info, col_edit, col_delete = st.columns([6, 0.5, 0.5])

                with col_info:
                    st.write(f"**질문 ID**: {q_id}")
                    st.write(f"**질문 내용**: {q_txt}")
                    st.write(f"**Keyword**: {q_kw}")
                    st.write(f"**유형**: {q_type_kor}")
                    if q_opts:
                        st.write(f"**옵션**: {q_opts}")

                with col_edit:
                    if st.button("수정", key=f"edit_{q_id}"):
                        st.session_state[f"editing_{q_id}"] = True
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
