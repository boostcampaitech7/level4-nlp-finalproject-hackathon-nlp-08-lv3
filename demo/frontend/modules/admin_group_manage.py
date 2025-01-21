import streamlit as st
import requests

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
                        for user in group_users:
                            cols = st.columns([4, 1])
                            with cols[0]:
                                st.write(user["name"])
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
                        st.write("### 부서 인원 추가")
                        available_user_names = [u["name"] for u in other_users]
                        selected_user = st.selectbox("추가할 사용자를 선택하세요", ["선택"] + available_user_names, key=f"select_user_{group_id}")

                        if st.button("추가", key=f"add_user_{group_id}_{selected_user}"):  # 키에 group_id와 선택 사용자 추가
                            if selected_user != "선택":
                                user_id = next(u["id"] for u in other_users if u["name"] == selected_user)
                                add_response = requests.post(
                                    f"{API_BASE_URL}/groups/{group_id}/users/{user_id}"
                                )
                                if add_response.status_code == 200:
                                    st.success(f"'{selected_user}' 추가 성공")
                                    st.rerun()
                                else:
                                    st.error(f"추가 실패: {add_response.json().get('message', '')}")
                            else:
                                st.warning("추가할 인원를 선택해주세요.")
                    else:
                        st.error("사용자 목록 조회 실패")

    else:
        st.error("부서 목록 조회 실패")