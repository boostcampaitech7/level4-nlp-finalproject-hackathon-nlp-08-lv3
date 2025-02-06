import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

# 세션 상태 초기화
if "mailjet_authenticated" not in st.session_state:
    st.session_state.mailjet_authenticated = False
if "mailjet_api_key" not in st.session_state:
    st.session_state.mailjet_api_key = None
if "mailjet_secret_key" not in st.session_state:
    st.session_state.mailjet_secret_key = None
    
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
    st.markdown("---")
    
    st.write("##### 📨 Mailjet 인증")
    
        # 세션에 Mailjet 인증 여부가 기록되어 있지 않다면 인증 창 표시
    if not st.session_state.mailjet_authenticated:
        st.warning("""저장된 Mailjet API 키 정보가 없습니다. 인증이 필요합니다.\n\nhttps://www.mailjet.com/ 에 접속하여 회원 가입시 사용한 Email 로 API KEY 및 SECRET KEY를 발급 받아주세요.""")
        
        # API 키 입력 필드
        api_key = st.text_input("Mailjet API KEY", type="password")
        secret_key = st.text_input("Mailjet SECRET KEY", type="password")
        
        # 인증 버튼
        if st.button("Mailjet 인증하기"):
            if not api_key or not secret_key:
                st.error("API KEY와 SECRET KEY를 모두 입력해주세요.")
            else:
                # 백엔드로 키 전송
                payload = {"API_KEY": api_key, "SECRET_KEY": secret_key}
                try:
                    res = requests.post(f"{API_BASE_URL}/mailjet-key", json=payload)
                    if res.status_code == 200 and res.json().get("success"):
                        # 인증 성공 시 세션 상태 업데이트
                        st.session_state.mailjet_authenticated = True
                        st.session_state.mailjet_api_key = api_key
                        st.session_state.mailjet_secret_key = secret_key
                        st.success("Mailjet 인증이 완료되었습니다.")
                        st.rerun()  # 페이지 새로고침
                    else:
                        # 인증 실패 시 오류 메시지 표시
                        error_message = res.json().get("message", "알 수 없는 오류가 발생했습니다.")
                        st.error(f"Mailjet 인증에 실패했습니다: {error_message}")
                except requests.exceptions.RequestException as e:
                    st.error(f"백엔드 서버 연결에 실패했습니다: {str(e)}")
    else:
        # 인증 완료 상태 표시
        st.success("Mailjet 인증이 완료되었습니다.")
        
        # 저장된 키 정보 표시 (옵션)
        if st.checkbox("저장된 Mailjet 키 정보 보기"):
            if hasattr(st.session_state, 'mailjet_api_key'):
                len_api_key = len(st.session_state.mailjet_api_key) - 4
                masked_api = st.session_state.mailjet_api_key[:4] + '*' * len_api_key
                with st.expander(f"API KEY: {masked_api}"):
                    st.code(st.session_state.mailjet_api_key)

            # 시크릿 키 표시 제거
            if hasattr(st.session_state, 'mailjet_secret_key'):
                st.warning("SECRET KEY 는 보여지지 않습니다", icon="🔒",)
        
        # 인증 해제 버튼 (옵션)
        if st.button("Mailjet 인증 해제"):
            st.session_state.mailjet_authenticated = False
            st.session_state.mailjet_api_key = None
            st.session_state.mailjet_secret_key = None
            st.success("Mailjet 인증이 해제되었습니다.")
            st.rerun()
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
