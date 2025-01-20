import os
import streamlit as st
from langchain_upstage import UpstageDocumentParseLoader
import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
import time

load_dotenv()

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
API_BASE_URL = "http://localhost:5000/api"
os.environ["UPSTAGE_API_KEY"] = UPSTAGE_API_KEY

def parse_evaluation_form(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    evaluation_data = {
        "title": soup.find('h1').text.strip() if soup.find('h1') else "인사고과 평가표",
        "questions": []
    }
    
    current_category = None
    for row in soup.find_all('tr')[3:]:  # 헤더 행 제외
        cells = row.find_all('td')
        if not cells:
            continue
            
        # 카테고리(업적/능력/태도) 확인
        first_cell = cells[0]
        if 'rowspan' in first_cell.attrs:
            current_category = first_cell.text.strip()
            evaluation_item = cells[1].text.strip()
            criteria = cells[2].text.strip()
        else:
            evaluation_item = cells[0].text.strip()
            criteria = cells[1].text.strip()
            
        if evaluation_item and criteria and current_category:
            evaluation_data["questions"].append({
                "keyword": current_category,
                "evaluation_item": evaluation_item,
                "criteria": criteria,
                "question_type": "single_choice",
                "options": ["매우우수", "우수", "보통", "미흡", "매우미흡"]
            })
    
    return evaluation_data

def display_evaluation_form(evaluation_data):
    st.title(evaluation_data["title"])
    
    # 임시 저장용 폼 데이터 초기화
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    
    # 카테고리별로 그룹화
    categories = set(q["keyword"] for q in evaluation_data["questions"])
    
    for category in categories:
        with st.expander(f"📋 {category}", expanded=True):
            category_questions = [q for q in evaluation_data["questions"] if q["keyword"] == category]
            
            for idx, question in enumerate(category_questions):
                question_key = f"{category}_{idx}"
                
                # 폼 데이터 초기화
                if question_key not in st.session_state.form_data:
                    st.session_state.form_data[question_key] = {
                        "include": True,
                        "question_type": "single_choice",
                        "options": "매우우수,우수,보통,미흡,매우미흡"
                    }
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**{question['evaluation_item']}**")
                    st.markdown(f"<div style='background-color: gray; padding: 5px 10px; border-radius: 10px; display: inline-block;'>질문</div> : {question['criteria']}", unsafe_allow_html=True)
                
                with col2:
                    st.session_state.form_data[question_key]["include"] = st.checkbox(
                        "포함",
                        key=f"include_{question_key}",
                        value=st.session_state.form_data[question_key].get("include", True)
                    )
                
                with col3:
                    st.session_state.form_data[question_key]["question_type"] = st.selectbox(
                        "질문 유형",
                        ["single_choice", "multi_choice", "subjective"],
                        key=f"type_{question_key}",
                        index=["single_choice", "multi_choice", "subjective"].index(
                            st.session_state.form_data[question_key]["question_type"]
                        )
                    )
                
                with col4:
                    st.session_state.form_data[question_key]["options"] = st.text_input(
                        "옵션 입력 (쉼표로 구분)",
                        value=st.session_state.form_data[question_key]["options"],
                        key=f"options_{question_key}"
                    )
                
                st.markdown("---")

def process_selected_questions():
    selected_questions = []
    
    for key, data in st.session_state.form_data.items():
        if data["include"]:
            category = key.split('_')[0]
            idx = int(key.split('_')[1])
            
            # 해당 카테고리의 질문들 찾기
            category_questions = [q for q in st.session_state.evaluation_data["questions"] 
                               if q["keyword"] == category]
            
            question_data = {
                "keyword": category,
                "question": category_questions[idx]["criteria"],  # criteria를 question으로 사용
                "question_type": data["question_type"],
                "options": [opt.strip() for opt in data["options"].split(",")]
            }
            selected_questions.append(question_data)
    
    return selected_questions

def question_add_from_pdf_page():
    st.title("파일로 질문 추가")
    
    uploaded_file = st.file_uploader(
        "파일 업로드",
        type=["pdf", "jpeg", "png", "bmp", "tiff", "heic", "docx", "xlsx", "pptx"]
    )

    if uploaded_file is not None:
        if uploaded_file.size > 50 * 1024 * 1024:
            st.error("파일 크기는 50MB를 초과할 수 없습니다.")
            return

        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        
        try:
            with st.spinner("파일 업로드 중..."):
                response = requests.post(f"{API_BASE_URL}/upload_file", files=files)

            if response.status_code == 200 and response.json().get("success"):
                st.success("파일 업로드 성공!")

                uploaded_folder = "../backend/uploads"
                saved_file_path = os.path.join(uploaded_folder, uploaded_file.name)
                
                with st.spinner("문서 분석 중..."):
                    loader = UpstageDocumentParseLoader(saved_file_path)
                    pages = loader.load()
                    
                    # HTML 파싱 및 평가표 표시
                    evaluation_data = parse_evaluation_form(str(pages[0]))
                    st.session_state.evaluation_data = evaluation_data
                    display_evaluation_form(evaluation_data)
                    
                    # 저장 버튼
                    if st.button("질문 저장", key="save_button"):
                        selected_questions = process_selected_questions()
                        if selected_questions:
                            st.success("선택한 질문이 저장되었습니다!")
                            st.table(pd.DataFrame(selected_questions))
                        else:
                            st.warning("저장할 질문이 없습니다.")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("적용", key="apply_button"):
                            selected_questions = process_selected_questions()
                            if selected_questions:
                                success = True
                                for question in selected_questions:
                                    payload = {
                                        "keyword": question["keyword"],
                                        "question_text": question["question"],
                                        "question_type": question["question_type"],
                                        "options": ','.join(question["options"]).strip() if question["options"] else None
                                    }
                                    r2 = requests.post(f"{API_BASE_URL}/questions", json=payload)
                                    if r2.status_code != 200:
                                        st.error(f"질문 저장 실패: {r2.text}")
                                        success = False
                                if success:
                                    st.success("질문이 성공적으로 적용되었습니다")
                                    time.sleep(2)
                                    st.session_state.page = "login"
                                    st.rerun()
                            else:
                                st.warning("적용할 질문이 없습니다.")
                    
                    with col2:
                        if st.button("취소", key="cancel_button"):
                            st.session_state.page = "login"
                            st.rerun()
                    
            else:
                st.error(response.json().get("message", "파일 업로드 실패"))
                
        except Exception as e:
            st.error(f"문서 처리 중 오류가 발생했습니다: {str(e)}")

