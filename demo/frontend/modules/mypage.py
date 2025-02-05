import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

def admin_mypage():
    st.subheader("👤 마이페이지")
    
    # 관리자 정보 조회
    response = requests.get(f"{API_BASE_URL}/users")
    current_admin = None
    
    if response.status_code == 200 and response.json().get("success"):
        users = response.json()["users"]
        current_admin = next((user for user in users if user["username"] == st.session_state.username), None)
    
    admin_email = current_admin.get("email", "이메일 없음") if current_admin else "이메일 없음"
    admin_name = st.session_state.name if "name" in st.session_state else "이름 없음"
    admin_role = "관리자"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info(f"👤 이름: {admin_name}")
    with col2:
        st.info(f"🏷️ 역할: {admin_role}")
    with col3:
        st.info(f"✉️ 이메일: {admin_email}")

def user_mypage():
    st.subheader("👤 마이페이지")
    
    # 사용자 정보 조회
    response = requests.get(f"{API_BASE_URL}/users")
    current_user = None
    
    if response.status_code == 200 and response.json().get("success"):
        users = response.json()["users"]
        current_user = next((user for user in users if user["username"] == st.session_state.username), None)
    
    group_name = current_user.get("group_name", "소속 없음") if current_user else "소속 없음"
    rank = current_user.get("rank", "직급 없음") if current_user else "직급 없음"
    user_name = st.session_state.name if "name" in st.session_state else "이름 없음"
    user_email = current_user.get("email", "이메일 없음") if current_user else "이메일 없음"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info(f"👥 소속: {group_name}")
    with col2:
        st.info(f"🏷️ 직급: {rank}")
    with col3:
        st.info(f"👤 이름: {user_name}")
    with col4:
        st.info(f"✉️ 이메일: {user_email}")
    
    st.markdown("---")
    st.markdown("### 📊 활동 통계")
    
    written_reviews = 0
    received_reviews = 0
    
    try:
        written_response = requests.get(
            f"{API_BASE_URL}/feedback/count/written/{st.session_state.username}"
        )
        if written_response.status_code == 200 and written_response.json().get("success"):
            written_reviews = written_response.json().get("count")
            
        received_response = requests.get(
            f"{API_BASE_URL}/feedback/count/received/{st.session_state.username}"
        )
        if received_response.status_code == 200 and received_response.json().get("success"):
            received_reviews = received_response.json().get("count")
    except Exception as e:
        st.error("통계 데이터를 가져오는 중 오류가 발생했습니다.")
        print(f"Error fetching review statistics: {e}")
    
    stat_col1, stat_col2 = st.columns(2)
    
    with stat_col1:
        st.info(f"✍️ 작성한 리뷰: {written_reviews}건")
    with stat_col2:
        st.info(f"📥 받은 리뷰: {received_reviews}건")
