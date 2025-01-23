import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 기본 폰트 설정 (한글 지원 가능)
rcParams['font.family'] = "DejaVu Sans"

def admin_feedback_summary(df_fb):
    # 취소 버튼
    if st.button("🔙 Go Back"):
        st.session_state.page = "feedback"
        st.rerun()
    
    st.write("## Peer Feedback Summary and Visualization")

    # 객관식 문항(Q1 ~ Q25) 데이터만 필터링
    df_fb_obj = df_fb[df_fb['질문ID'].astype(int) <= 25]
    
    # 점수 매핑
    score_map = {
        "매우우수": 5,
        "우수": 4,
        "보통": 3,
        "미흡": 2,
        "매우미흡": 1
    }
    df_fb_obj['점수'] = df_fb_obj['답변'].map(score_map)
    
    # 문항별 범주 설정
    category_map = {
        "Achievement": range(1, 4),    # Q1 ~ Q3
        "Attitude": range(4, 10),     # Q4 ~ Q9
        "Ability": range(10, 18),     # Q10 ~ Q17
        "Leadership": range(18, 22),  # Q18 ~ Q21
        "Collaboration": range(22, 26)  # Q22 ~ Q25
    }
    
    # 범주별 평균 점수 계산
    category_scores = {}
    for category, questions in category_map.items():
        category_scores[category] = df_fb_obj[df_fb_obj['질문ID'].astype(int).isin(questions)]['점수'].mean()
    
    # 레이더 차트 데이터 설정
    labels = list(category_scores.keys())
    values = list(category_scores.values())
    values += values[:1]  # 레이더 차트를 닫기 위해 처음 값을 다시 추가

    # 레이더 차트 설정
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))  # 크기 조정
    ax.fill(angles, values, color='skyblue', alpha=0.4)  # 내부 색상 변경
    ax.plot(angles, values, color='blue', linewidth=2)  # 선 두께 강조
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=10)  # y축 레이블 크기 조정
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=12)  # x축 레이블 크기 조정

    # 제목 추가
    ax.set_title("Peer Feedback Radar Chart", fontsize=16, pad=20)

    # 그래프 보여주기
    st.pyplot(fig)

    # 종합 평가 서술
    st.write("### Overall Assessment")
    for category, score in category_scores.items():
        st.write(f"- **{category}**: Average Score {score:.2f}")
