import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from io import BytesIO
from langchain_upstage import UpstageEmbeddings
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# API 키 가져오기
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# 기본 폰트 설정 (한글 지원 가능)
rcParams['font.family'] = "DejaVu Sans"

# 점수 매핑
score_map = {
    "매우우수": 5,
    "우수": 4,
    "보통": 3,
    "미흡": 2,
    "매우미흡": 1
}

# 문항별 범주 설정
category_map = {
    "Achievement": range(1, 4),    # Q1 ~ Q3
    "Attitude": range(4, 10),     # Q4 ~ Q9
    "Ability": range(10, 18),     # Q10 ~ Q17
    "Leadership": range(18, 22),  # Q18 ~ Q21
    "Collaboration": range(22, 26)  # Q22 ~ Q25
}

# 레이더 차트 생성 함수
def create_radar_chart(category_scores):
    labels = list(category_scores.keys())
    values = list(category_scores.values())
    values += values[:1]  # 레이더 차트를 닫기 위해 처음 값을 추가

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    # 내부 색상과 외곽선 색상 변경
    ax.fill(angles, values, color='#94c4f0', alpha=0.4)  # 내부 색상 (파스텔 블루)
    ax.plot(angles, values, color='#2b8cd8', linewidth=2)  # 외곽선 색상 (짙은 파랑)

    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)

    ax.set_title("Peer Feedback Radar Chart", fontsize=16, pad=20)

    return fig


# 관리자 피드백 요약 화면
# 관리자 피드백 요약 화면
def admin_feedback_summary(df_fb):
    # Q1~Q25 데이터 필터링
    df_fb_obj = df_fb[df_fb['질문ID'].astype(int) <= 25]
    df_fb_obj['점수'] = df_fb_obj['답변'].map(score_map)

    # Q26~Q27 데이터 필터링
    df_fb_extra = df_fb[df_fb['질문ID'].astype(int) > 25]

    # 범주별 평균 점수 계산
    category_scores = {}
    for category, questions in category_map.items():
        scores = df_fb_obj[df_fb_obj['질문ID'].astype(int).isin(questions)]['점수']
        category_scores[category] = scores.mean()

    # Total 및 Average 계산
    total_score = round(sum(category_scores.values()), 2)
    average_score = round(np.mean(list(category_scores.values())), 2)

    # 레이더 차트 생성 (범주 점수만 사용)
    radar_chart_fig = create_radar_chart({
        key: value for key, value in category_scores.items() if key not in ["Total", "Average"]
    })

    # 화면 구성
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.subheader("Category Scores Table")
        table_data = pd.DataFrame.from_dict(category_scores, orient='index', columns=['Scores'])
        table_data.loc["Total"] = total_score
        table_data.loc["Average"] = average_score

        # 소수점 둘째 자리까지 표시
        table_data['Scores'] = table_data['Scores'].apply(lambda x: f"{x:.2f}")
        st.table(table_data)

    with col2:
        st.subheader("Radar Chart")
        st.pyplot(radar_chart_fig)

    st.markdown("---")

    col1, col2 = st.columns(2, gap="large")
    with col1:
        # Q26~Q27 데이터를 표로 표시
        st.subheader("Overall Assessment (Q26 & Q27)")
        if not df_fb_extra.empty:
            st.dataframe(df_fb_extra[['질문ID', '작성자', '답변']])
        else:
            st.write("Q26~Q27 데이터가 없습니다.")

    with col2:
        st.subheader("Recommendation")
        st.write("돈의 속성의 책을 추천합니다.")

    st.markdown("---")

    if not df_fb_extra.empty:
        st.subheader("Overall Feedback Summary")

        # Q26~Q27 답변들 결합
        all_feedback = " ".join(df_fb_extra['답변'].tolist())

        # 요약 함수
        def summarize_feedback(text):
            try:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                model_name = "lcw99/t5-base-korean-text-summary"
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

                inputs = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=512, truncation=True)
                summary_ids = model.generate(inputs, num_beams=4, max_length=150, early_stopping=True)
                return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            except Exception as e:
                return f"요약 실패: {str(e)}"

        # 요약 수행
        summary = summarize_feedback(all_feedback)

        # 요약 결과 표시
        st.text_area("Summary of Overall Feedback", summary, height=150)
