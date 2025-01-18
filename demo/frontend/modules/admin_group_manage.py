### 그룹 수정 시작
import streamlit as st
import requests

API_BASE_URL = "http://localhost:5000/api"

def admin_manage_groups():
    st.write("## 사용자 그룹 관리")

    # 그룹 생성
    st.write("---")
    st.subheader("그룹 생성")
    new_group_name = st.text_input("새 그룹 이름을 입력하세요")
    if st.button("그룹 생성"):
        if new_group_name.strip():
            response = requests.post(f"{API_BASE_URL}/groups/create", 
                json={"group_name": new_group_name.strip()})
            if response.status_code == 200:
                st.success(f"그룹 '{new_group_name}' 생성 성공")
                st.rerun()
            else:
                st.error(f"그룹 생성 실패: {response.json().get('message', '')}")
        else:
            st.warning("그룹 이름을 입력해주세요")

    # 그룹 목록 조회
    st.write("---")
    st.subheader("그룹 목록")
    
    response = requests.get(f"{API_BASE_URL}/groups")
    if response.status_code == 200:
        groups = response.json().get("groups", [])
        
        if groups:
            for group in groups:
                group_id = group["id"]
                group_name = group["group_name"]
                cols = st.columns([4, 1, 1])
                with cols[0]:
                    st.write(f"**{group_name}**")
                with cols[1]:
                    if st.button("수정", key=f"edit_{group_id}"):
                        st.session_state.editing_group_id = group_id
                        st.session_state.editing_group_name = group_name
                        st.rerun()
                with cols[2]:
                    if st.button("삭제", key=f"delete_{group_id}"):
                        delete_response = requests.delete(f"{API_BASE_URL}/groups/delete/{group_id}")
                        if delete_response.status_code == 200:
                            st.success(f"그룹 '{group_name}' 삭제 성공")
                            st.rerun()
                        else:
                            st.error(f"그룹 삭제 실패: {delete_response.json().get('message', '')}")
        else:
            st.info("생성된 그룹이 없습니다.")
    else:
        st.error("그룹 목록 조회 실패")

    # 그룹 수정 및 사용자 관리
    if "editing_group_id" in st.session_state:
        group_id = st.session_state.editing_group_id
        group_name = st.session_state.editing_group_name

        st.write("---")
        st.subheader(f"그룹 수정: {group_name}")

        # 사용자 목록 조회
        response = requests.get(f"{API_BASE_URL}/users")
        if response.status_code == 200:
            users = response.json().get("users", [])
            
            # 현재 그룹 사용자 조회
            group_users = [u for u in users if u.get("group_id") == group_id]
            other_users = [u for u in users if u.get("group_id") != group_id]

            st.write("### 현재 그룹 사용자")
            if group_users:
                for user in group_users:
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.write(user["name"])
                    with cols[1]:
                        if st.button("삭제", key=f"remove_user_{user['id']}"):
                            # API 호출하여 사용자 제거
                            remove_response = requests.delete(
                                f"{API_BASE_URL}/groups/{group_id}/users/{user['id']}")
                            if remove_response.status_code == 200:
                                st.success(f"사용자 '{user['name']}' 삭제 성공")
                                st.rerun()
                            else:
                                st.error("사용자 삭제 실패")
            else:
                st.info("현재 그룹에 사용자가 없습니다.")

            st.write("### 사용자 추가")
            if other_users:
                selected_user = st.selectbox(
                    "추가할 사용자를 선택하세요",
                    ["선택"] + [u["name"] for u in other_users]
                )
                if st.button("추가"):
                    if selected_user != "선택":
                        user_id = next(u["id"] for u in other_users if u["name"] == selected_user)
                        # API 호출하여 사용자 추가
                        add_response = requests.post(
                            f"{API_BASE_URL}/groups/{group_id}/users/{user_id}")
                        if add_response.status_code == 200:
                            st.success(f"사용자 '{selected_user}' 추가 성공")
                            st.rerun()
                        else:
                            st.error("사용자 추가 실패")
                    else:
                        st.warning("추가할 사용자를 선택해주세요.")
            else:
                st.info("추가 가능한 사용자가 없습니다.")
        else:
            st.error("사용자 목록 조회 실패")
### 그룹 수정 끝