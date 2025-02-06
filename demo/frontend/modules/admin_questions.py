import streamlit as st
import requests
import json
from streamlit_tags import st_tags
import time
import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
API_BASE_URL = "http://localhost:5000/api"

client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

def get_question_suggestions(keyword):
    prompt = f"""
    당신은 직장에서 쓰일 동료 피드백 질문 생성 전문가입니다.
    '{keyword}' 키워드와 관련된 동료 평가용 질문 3개 (객관식 2개, 주관식 1개)를 생성해주세요.
    
    규칙:
    1. 각 질문은 구체적이고 명확해야 합니다
    2. 질문과 함께 질문 유형(객관식, 주관식)도 표시해주세요
    3. 객관식인 경우 선택지도 함께 제시해주세요
    
    키워드가 리더쉽인 경우
    형식:
    [질문1]
    - 유형: (질문 유형)
    - 질문: (질문 내용)
    - (객관식일 경우) 선택지: 매우우수, 우수, 보통, 미흡, 매우미흡

    객관식 예시 응답:
    [질문1]
    - 유형: 객관식
    - 질문: 팀원의 역량 개발을 위해 성과와 능력을 주기적으로 점검하고 개선 방향을 제시한다. 단순 지적이 아니라 구체적이고 건설적인 피드백을 제공한다.
    - 선택지: 매우우수, 우수, 보통, 미흡, 매우미흡

    주관식 예시 응답:
    [질문1]
    - 유형: 주관식
    - 질문: 팀원의 리더십 스타일은 어떠한지 구체적인 설명과 함께 작성해주세요.
    """

    try:
        response = client.chat.completions.create(
            model="solar-pro",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"질문 생성 중 오류가 발생했습니다: {str(e)}"

def admin_manage_questions():
    st.write("## 📝 리뷰 관리")
    
    tab_manage, tab_preview, tab_deadline = st.tabs(["편집", "미리보기", "기간 설정"])
    if 'edit_completed' not in st.session_state:
        st.session_state.edit_completed = False
    if 'show_confirm' not in st.session_state:
        st.session_state.show_confirm = False
    
    with tab_manage:
        if st.session_state.show_confirm:
            st.warning("⚠️ 주의: 확인 시 질문지 수정이 더 이상 불가능합니다. 편집을 완료 하시겠습니까?")
            col_confirm, col_cancel = st.columns([1, 13])
            with col_confirm:
                if st.button("확인"):
                    st.session_state.edit_completed = True
                    st.session_state.show_confirm = False
                    keyword = set()
                    long_q = ["(대상자)가 이 영역을 개선하기 위한 1-2가지 방법은 무엇인가요?", "(대상자)가 이 영역에서 잘한 1-2가지 사항은 무엇인가요?"]
                    resp = requests.get(f"{API_BASE_URL}/questions")
                    if resp.status_code == 200 and resp.json().get("success"):
                        questions = resp.json()["questions"]
                        existing_long_q = {(q["question_text"], q['keyword']) for q in questions if q["question_type"] == "long_answer"}
                        for q in questions:
                            keyword.add(q["keyword"])
                        for key in keyword:
                            for lq in long_q:
                                if (lq, key) not in existing_long_q:
                                    payload = {
                                        "keyword": key,
                                        "question_text": lq,
                                        "question_type": "long_answer",
                                        "options": None
                                    }
                                    r2 = requests.post(f"{API_BASE_URL}/questions", json=payload)
                                    if r2.status_code == 200 and r2.json().get("success"):
                                        pass
                    st.rerun()
            with col_cancel:
                if st.button("취소"):
                    st.session_state.show_confirm = False
                    st.rerun()
            st.stop()

        if st.session_state.edit_completed:
            st.info("질문지 수정이 완료되었습니다. 질문지를 확인하고 싶으신 경우, 미리보기를 이용해주세요.")
        else:
        # 편집 완료 버튼 (상단 고정)
            st.button("질문지 편집 완료", 
                    on_click=lambda: setattr(st.session_state, 'show_confirm', True),
                    type="primary",
                    key="complete_edit_button",
                    help="⚠️ 주의: 편집 완료 후에는 수정이 불가능합니다")

            keywords = st_tags(
                label='### 🏷️ 키워드 목록 작성',
                text='키워드를 입력하고 Enter를 누르세요',
                value=['업적','능력','리더십','협업','태도'],
                suggestions=[
                    "창의성", "책임감", "효율성", "리더십", "협업", 
                    "정확성", "적응력", "분석력", "열정", "신뢰성", 
                    "시간관리", "투명성", "결정력", "성실성", 
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

                # 키워드별로 질문 그룹화
                keyword_questions = {}
                for q in questions:
                    kw = q["keyword"] or "미분류"
                    if kw not in keyword_questions:
                        keyword_questions[kw] = []
                    keyword_questions[kw].append(q)

                type_map = {
                    "single_choice": "객관식(단일)",
                    "long_answer": "주관식"
                }

                with st.expander("질문 추가하기", expanded=False):
                    new_kw = st.selectbox("keyword", options=keywords, key="new_kw")
                    
                    if st.button("🤖 AI 질문 추천받기"):
                        with st.spinner("AI가 키워드에 맞는 추천 질문을 생성중입니다..."):
                            suggested_questions = get_question_suggestions(new_kw)
                            st.text_area("추천 질문", 
                                        value=suggested_questions, 
                                        height=300)
                            st.info("위의 추천 질문을 복사할 수 있습니다.")
                    
                    new_text = st.text_input("질문", key="new_text")
                    new_type = st.selectbox("질문 유형", 
                                        ["single_choice","long_answer"],
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
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("질문 추가에 실패했습니다.")

                # 키워드별로 질문 표시
                for keyword in sorted(keyword_questions.keys()):
                    st.markdown(f"""
                        <div style="background-color: #E8F6F3; padding: 20px; border-radius: 15px; margin: 25px 0; 
                                border-left: 5px solid #16A085; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h3 style="color: #16A085; margin: 0; font-size: 1.3em;">{keyword}</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for q in reversed(keyword_questions[keyword]):
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

                        if is_editing:
                            st.markdown(f"<p style='color: #666; font-size: 0.9em;'>ID: {q_id}</p>", 
                                      unsafe_allow_html=True)
                            
                            if q_kw not in keywords:
                                st.error(f"'{q_kw}' 는 키워드 목록에 없습니다. '{q_kw}' 를 키워드 목록에 추가해주세요.")
                            else:
                                edit_kw = st.selectbox("Keyword", options=keywords, 
                                                     index=keywords.index(q_kw) if q_kw in keywords else 0, 
                                                     key=f"edit_kw_{q_id}")
                                edit_text = st.text_input("질문", value=q_txt, key=f"edit_text_{q_id}")
                                edit_type = st.selectbox(
                                    "질문 유형",
                                    ["single_choice","long_answer"],
                                    index=["single_choice","long_answer"].index(q_type_db),
                                    key=f"edit_type_{q_id}"
                                )

                                if edit_type == "long_answer":
                                    edit_opts = ""
                                else:
                                    edit_opts = st.text_input("옵션", value=q_opts, key=f"edit_opts_{q_id}")

                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("수정 완료", key=f"save_{q_id}", 
                                           type="primary"):
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
                            col_info, col_buttons = st.columns([5, 1])

                            with col_info:
                                st.markdown(f"""
                                    <div style="padding: 10px 0;">
                                        <p style='color: #666; font-size: 0.9em; margin: 0;'>ID: {q_id}</p>
                                        <div style='display: flex; gap: 10px; margin: 8px 0;'>
                                            <span style='background-color: #D1F2EB; color: #16A085; 
                                                    padding: 3px 10px; border-radius: 12px; font-size: 0.9em;'>
                                                {q_type_kor}
                                            </span>
                                            <span style='background-color: #D1F2EB; color: #16A085; 
                                                    padding: 3px 10px; border-radius: 12px; font-size: 0.9em;'>
                                                {q_kw}
                                            </span>
                                        </div>
                                        <p style='font-size: 1.1em; margin: 8px 0;'>{q_txt}</p>
                                        {f"<p style='color: #666; font-size: 0.9em; margin-top: 8px;'>옵션: {q_opts}</p>" if q_opts else ""}
                                    </div>
                                """, unsafe_allow_html=True)

                            with col_buttons:
                                st.markdown("""
                                    <div style='display: flex; gap: 10px; justify-content: flex-end; 
                                            align-items: center; height: 100%;'>
                                """, unsafe_allow_html=True)
                                if st.button("수정", key=f"edit_{q_id}", 
                                           help="질문 수정"):
                                    st.session_state[f"editing_{q_id}"] = True
                                    st.rerun()
                                if st.button("삭제", key=f"delete_{q_id}", 
                                           help="질문 삭제"):
                                    resp_del = requests.delete(f"{API_BASE_URL}/questions/{q_id}")
                                    if resp_del.status_code == 200 and resp_del.json().get("success"):
                                        st.rerun()
                                    else:
                                        st.error("질문 삭제 실패")
                                st.markdown("</div>", unsafe_allow_html=True)

                        if not is_editing:
                            st.markdown("""
                                <hr style='margin: 8px 0; 
                                         border: none; 
                                         border-top: 1px solid #e0e0e0; 
                                         background-color: transparent;'>
                            """, unsafe_allow_html=True)
            else:
                st.error("질문 목록 조회 실패")

    with tab_preview:
        preview_questions()
        
    with tab_deadline:
        admin_manage_deadline()

    st.markdown("---")

def admin_manage_deadline():
    st.write("### 🗓️ 피드백 제출 기간 설정")
    
    resp = requests.get(f"{API_BASE_URL}/deadline")
    current_start_date = None
    current_deadline = None
    if resp.status_code == 200 and resp.json().get("success"):
        current_start_date = resp.json().get("start_date")
        current_deadline = resp.json().get("deadline")
        
    if current_start_date and current_deadline:
        st.info(f"현재 설정된 기간: {current_start_date} ~ {current_deadline}")
    
    st.write("#### 시작일 설정")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "시작일",
            min_value=datetime.date.today()
        )
    
    with col2:
        start_time = st.text_input(
            "시작 시간",
            value="09:00",
            help="24시간 형식으로 입력해주세요 (예: 09:00)",
            placeholder="HH:MM"
        )
        
        try:
            hour, minute = map(int, start_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                st.error("올바른 시간 형식이 아닙니다.")
                return
            new_start_time = datetime.time(hour, minute)
        except:
            st.error("HH:MM 형식으로 입력해주세요 (예: 09:00)")
            return
            
    st.write("#### 마감일 설정")
    col3, col4 = st.columns(2)
    
    with col3:
        end_date = st.date_input(
            "마감일",
            min_value=start_date
        )
    
    with col4:
        end_time = st.text_input(
            "마감 시간",
            value="23:59",
            help="24시간 형식으로 입력해주세요 (예: 14:30)",
            placeholder="HH:MM"
        )
        
        try:
            hour, minute = map(int, end_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                st.error("올바른 시간 형식이 아닙니다.")
                return
            new_end_time = datetime.time(hour, minute)
        except:
            st.error("HH:MM 형식으로 입력해주세요 (예: 14:30)")
            return
    
    st.write("#### 리마인드 설정")
    col5, col6 = st.columns(2)
    
    with col5:
        remind_days = st.number_input(
            "마감일 며칠 전부터 알림을 보낼까요?",
            min_value=0,
            max_value=14,
            value=3,
            step=1,
            help="0-14 사이로 설정해주세요"
        )
    
    with col6:
        remind_time = st.text_input(
            "하루 중 알림 시간",
            value="10:00",
            help="24시간 형식으로 입력해주세요(예: 09:00)",
            placeholder="HH:MM"
        )
        
        try:
            hour, minute = map(int, remind_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                st.error("올바른 시간 형식이 아닙니다.")
                return
        except:
            st.error("HH:MM 형식으로 입력해주세요 (예: 09:00)")
            return
    
    if st.button("기간 설정"):
        start_datetime = datetime.datetime.combine(start_date, new_start_time)
        end_datetime = datetime.datetime.combine(end_date, new_end_time)
        current_datetime = datetime.datetime.now()
        
        if start_datetime <= current_datetime:
            st.error("시작 기한은 현재 시점 이후로 설정해주세요.")
            return
            
        if end_datetime <= start_datetime:
            st.error("마감 기한은 시작 기한 이후로 설정해주세요.")
            return
            
        remind_start_date = end_datetime - datetime.timedelta(days=remind_days)
        remind_hour, remind_minute = map(int, remind_time.split(':'))
        remind_start_datetime = remind_start_date.replace(hour=remind_hour, minute=remind_minute)
        
        if remind_start_datetime <= current_datetime:
            st.error("리마인드 설정이 유효하지 않습니다. 현재 시점 이후로 설정해주세요.")
            return
            
        payload = {
            "start_date": start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "deadline": end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "remind_days": remind_days,
            "remind_time": remind_time
        }
        resp = requests.post(f"{API_BASE_URL}/deadline", json=payload)
        if resp.status_code == 200 and resp.json().get("success"):
            st.success("기한 설정이 완료되었습니다.")
            time.sleep(2)
            st.rerun()
        else:
            error_msg = resp.json().get("message", "알 수 없는 오류가 발생했습니다.")
            st.error(f"설정에 실패했습니다: {error_msg}")

def preview_questions():
    st.write("### 👀 미리보기")
    st.info("이 화면은 미리보기 전용입니다. 실제 제출 기능은 없습니다.")

    r_q = requests.get(f"{API_BASE_URL}/questions")
    if r_q.status_code == 200 and r_q.json().get("success"):
        questions = r_q.json()["questions"]
    else:
        st.error("질문 목록 불러오기 실패")
        return

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
                    chosen = st.radio(
                        "답변 선택",
                        opts,
                        key=f"{key_prefix}_radio",
                        horizontal=True,
                        index=None,
                        disabled=True
                    )
                answers[q_id] = chosen
                st.markdown("---")
            else:
                st.markdown(f"<p style='color: #666;'><strong>{q_text}</strong></p>", unsafe_allow_html=True)
                short_ans = st.text_input("답변 입력", key=f"{key_prefix}_text", disabled = True)
                answers[q_id] = short_ans

def question_add_page():
    st.title("질문 추가")

    new_kw = st.text_input("keyword")
    new_text = st.text_input("질문")
    new_type = st.selectbox("질문 유형", ["single_choice","long_answer"])

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
            ["single_choice", "long_answer"],
            index=["single_choice","long_answer"].index(old_type)
            if old_type in ["single_choice","long_answer"] else 0
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