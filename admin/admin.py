import streamlit as st

def admin_page():
    st.title("관리자 페이지")
    st.write("이곳은 관리자만 접근할 수 있는 페이지입니다.")

    with st.sidebar:
        st.header("관리자 메뉴")
        if st.button("Peer Feedback Form Creation"):
            st.session_state["page"] = "create_feedback_form"

        if st.button("View Feedback Form"):
            st.session_state["page"] = "view_feedback_form"

        if st.button("로그아웃"):
            st.session_state["page"] = "login"

def rerun_app():
    """Trigger app rerun using session state toggle."""
    st.session_state["placeholder"] = not st.session_state.get("placeholder", False)

def render_question_and_options(question_index):
    """Render the question and options block for a specific index."""
    question_key = f"current_question_{question_index}"
    options_key = f"current_options_{question_index}"
    type_key = f"question_type_{question_index}"

    question = st.text_area(
        "질문 내용을 입력하세요.",
        key=question_key,
        placeholder="여기에 질문을 입력하세요. 엔터 키로 줄바꿈이 가능합니다."
    )

    question_type = st.selectbox(
        "질문 유형을 선택하세요.",
        ["서술형", "객관식", "등급"],
        key=type_key
    )

    if question_type == "서술형":
        st.write("사용자는 이 질문에 텍스트로 응답합니다.")

    elif question_type == "객관식":
        st.write("### 항목 추가")
        options = st.session_state.get(options_key, [""])
        for idx, option in enumerate(options):
            col1, col2 = st.columns([4, 1])
            with col1:
                options[idx] = st.text_input(f"항목 {idx + 1}", value=option, key=f"{options_key}_{idx}")

            with col2:
                if st.button("삭제", key=f"delete_{options_key}_{idx}"):
                    options.pop(idx)
                    st.session_state[options_key] = options
                    rerun_app()

        if st.button("항목 추가", key=f"add_option_{question_key}"):
            options.append("")
            st.session_state[options_key] = options

    elif question_type == "등급":
        st.slider("등급을 선택하도록 설정하세요.", min_value=1, max_value=10, value=5, key=f"slider_{question_index}")

    return question, question_type, st.session_state.get(options_key, [])

def create_peer_feedback_form():
    st.title("Peer Feedback Form Creation")
    st.write("질문과 항목을 추가하고 피드백 폼을 생성하세요.")

    if "questions_with_options" not in st.session_state:
        st.session_state["questions_with_options"] = []

    if "current_question_blocks" not in st.session_state:
        st.session_state["current_question_blocks"] = 1

    # Title creation
    st.subheader("폼 제목 설정")
    title = st.text_input("폼 제목을 입력하세요.", key="form_title", placeholder="예: Peer Feedback Form")

    st.divider()

    # Render question blocks dynamically in columns
    left_col, right_col = st.columns(2)

    with left_col:
        for i in range(st.session_state["current_question_blocks"]):
            st.write(f"### 질문 {i + 1}")
            question, question_type, options = render_question_and_options(i)

            if st.button("질문 삭제", key=f"delete_question_{i}"):
                st.session_state["questions_with_options"].pop(i)
                st.session_state["current_question_blocks"] -= 1
                rerun_app()

            if question.strip():
                st.session_state["questions_with_options"].append({
                    "question": question,
                    "type": question_type,
                    "options": options
                })

    with right_col:
        if st.button("질문 추가"):
            st.session_state["current_question_blocks"] += 1
            rerun_app()

    st.divider()

    # Display saved questions and options at the bottom
    if st.session_state["questions_with_options"]:
        st.write("### 저장된 질문 목록")
        for idx, item in enumerate(st.session_state["questions_with_options"], start=1):
            st.divider()
            st.write(f"**{idx}. {item['question']}**")
            if item['type'] == "객관식":
                for opt_idx, opt in enumerate(item["options"], start=1):
                    st.write(f"  {opt_idx}. {opt}")
            elif item['type'] == "등급":
                st.write("등급형 질문")

    # Finalize the form
    if st.button("피드백 폼 생성 완료"):
        if title.strip() and st.session_state["questions_with_options"]:
            st.session_state["page"] = "view_feedback_form"
            st.session_state["form_title"] = title.strip()
        else:
            st.error("폼 제목과 최소 하나의 질문을 추가해야 합니다.")

    if st.button("관리자 페이지로 돌아가기"):
        st.session_state["page"] = "admin"

def view_feedback_form():
    st.title("Feedback Form")
    st.write("생성된 피드백 폼입니다.")

    if "form_title" in st.session_state:
        st.header(st.session_state["form_title"])

    if not st.session_state["questions_with_options"]:
        st.warning("아직 생성된 질문이 없습니다.")
    else:
        for idx, item in enumerate(st.session_state["questions_with_options"], start=1):
            st.divider()
            st.write(f"**{idx}. {item['question']}**")
            if item['type'] == "객관식":
                st.multiselect(
                    f"**{idx}. {item['question']}**",
                    options=item["options"],
                    default=[],
                    key=f"question_{idx}"
                )
            elif item['type'] == "등급":
                st.slider(
                    f"**{idx}. {item['question']}**",
                    min_value=1, max_value=10, value=5, key=f"slider_{idx}"
                )

    if st.button("관리자 페이지로 돌아가기"):
        st.session_state["page"] = "admin"

def user_page():
    st.title("사용자 페이지")
    st.write("이곳은 사용자만 접근할 수 있는 페이지입니다.")

    if "form_title" in st.session_state:
        st.header(st.session_state["form_title"])

    if not st.session_state["questions_with_options"]:
        st.warning("아직 생성된 질문이 없습니다.")
    else:
        st.write("### 피드백 폼 작성")
        for idx, item in enumerate(st.session_state["questions_with_options"], start=1):
            st.write(f"**{idx}. {item['question']}**")
            if item['type'] == "객관식":
                for option in item["options"]:
                    st.checkbox(option, key=f"{item['question']}_{option}")
            elif item['type'] == "등급":
                st.slider(
                    f"**{item['question']}**",
                    min_value=1, max_value=10, value=5, key=f"slider_{idx}"
                )

        if st.button("제출"):
            st.success("피드백이 제출되었습니다. 감사합니다!")
