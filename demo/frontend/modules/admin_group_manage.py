import streamlit as st
import requests
import time

API_BASE_URL = "http://localhost:5000/api"

def admin_manage_groups():
    st.write("## 부서 관리")

    # 부서 생성
    st.write("---")
    st.subheader("부서 생성")
    new_group_name = st.text_input("새 부서 이름을 입력하세요")
    if st.button("부서 생성"):
        if new_group_name.strip():
            response = requests.post(f"{API_BASE_URL}/groups/create", 
                json={"group_name": new_group_name.strip()})
            if response.status_code == 200:
                st.success(f"부서 '{new_group_name}' 생성 성공")
                st.rerun()
            else:
                st.error(f"부서 생성 실패: {response.json().get('message', '')}")
        else:
            st.warning("부서 이름을 입력해주세요")

    # 부서 목록 조회
    st.write("---")
    st.subheader("부서 목록 및 관리")
    response = requests.get(f"{API_BASE_URL}/groups")
    if response.status_code == 200:
        groups = response.json().get("groups", [])

        if groups:
            for group in groups:
                group_id = group["id"]
                group_name = group["group_name"]

                with st.expander(f"👥 {group_name}"):
                    # 부서 삭제 버튼
                    if st.button("부서 삭제", key=f"delete_group_{group_id}"):
                        delete_response = requests.delete(f"{API_BASE_URL}/groups/delete/{group_id}")
                        if delete_response.status_code == 200:
                            st.success(f"부서 '{group_name}' 삭제 성공")
                            st.rerun()
                        else:
                            st.error(f"부서 삭제 실패: {delete_response.json().get('message', '')}")

                    # 사용자 목록 조회
                    users_response = requests.get(f"{API_BASE_URL}/users")
                    if users_response.status_code == 200:
                        users = users_response.json().get("users", [])

                        # 현재 부서 사용자 및 기타 사용자 분리
                        group_users = [u for u in users if u.get("group_id") == group_id]
                        other_users = [u for u in users if u.get("group_id") != group_id and u.get("role") != "admin"]

                        # 현재 부서 사용자 표시
                        st.write("### 현재 부서 인원 조회")

                        # 팀장과 일반 사용자 분리
                        team_leaders = [u for u in group_users if u['rank'] == "팀장"]
                        other_members = [u for u in group_users if u['rank'] != "팀장"]

                        # 팀장 먼저 표시
                        for user in team_leaders + other_members:
                            cols = st.columns([4, 1])
                            with cols[0]:
                                rank = user['rank']
                                if rank == "팀장":
                                    st.markdown(f"<div style='display: inline-block; background-color: #ffcc00; border-radius: 5px; padding: 2px 5px; color: #000000; font-weight: bold; margin-right: 10px;'>{rank}</div>"
                                                f"<span style='color: #000000;'>{user['name']}</span>", 
                                                unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<div style='display: inline-block; background-color: #fae9a7; border-radius: 5px; padding: 2px 5px; color: #000000; font-weight: bold; margin-right: 10px;'>{rank}</div>"
                                                f"<span style='color: #000000;'>{user['name']}</span>", 
                                                unsafe_allow_html=True)
                            with cols[1]:
                                if st.button("삭제", key=f"remove_user_{group_id}_{user['id']}"):  # 키에 group_id 추가
                                    remove_response = requests.delete(
                                        f"{API_BASE_URL}/groups/{group_id}/users/{user['id']}"
                                    )
                                    if remove_response.status_code == 200:
                                        st.success(f"'{user['name']}' 삭제 성공")
                                        st.rerun()
                                    else:
                                        st.error(f"삭제 실패: {remove_response.json().get('message', '')}")

                        # 사용자 추가 기능
                        st.write("### 부서 이전")
                        
                        # 검색어 입력 필드
                        search_name = st.text_input(
                            "이전할 사용자 이름을 입력하세요 (검색)", 
                            key=f"search_user_{group_id}"
                        )
                        
                        # 검색어로 필터링된 사용자 목록
                        available_user_names = [u["name"] for u in other_users]
                        filtered_users = [
                            name for name in available_user_names 
                            if search_name.lower() in name.lower()
                        ] if search_name else available_user_names
                        
                        # 사용자 선택과 직급 선택을 나란히 배치
                        col1, col2 = st.columns(2)
                        with col1:
                            selected_user = st.selectbox(
                                "검색된 사용자 목록", 
                                ["선택"] + filtered_users,
                                key=f"select_user_{group_id}"
                            )
                        
                        with col2:
                            new_rank = st.selectbox(
                                "새로운 직급 선택",
                                ["팀장", "팀원"],
                                key=f"new_rank_{group_id}"
                            )

                        if st.button("이전", key=f"add_user_{group_id}_{selected_user}"):
                            if selected_user != "선택":
                                user_id = next(u["id"] for u in other_users if u["name"] == selected_user)
                                response = requests.post(
                                    f"{API_BASE_URL}/groups/{group_id}/users/{user_id}",
                                    json={"rank": new_rank}
                                )
                                if response.status_code == 200:
                                    data = response.json()
                                    prev_info = data["previous"]
                                    new_info = data["new"]
                                    success_msg = (
                                        f"'{prev_info['group_name']}'의 {prev_info['rank']} {prev_info['name']}님이 "
                                        f"'{new_info['group_name']}'의 {new_info['rank']}으로 이전되었습니다."
                                    )
                                    st.success(success_msg)
                                    time.sleep(5)
                                    st.rerun()
                                else:
                                    st.error("부서 이전에 실패했습니다.")
                            else:
                                st.warning("이전할 인원을 선택해주세요.")
                    else:
                        st.error("사용자 목록 조회 실패")

    else:
        st.error("부서 목록 조회 실패")