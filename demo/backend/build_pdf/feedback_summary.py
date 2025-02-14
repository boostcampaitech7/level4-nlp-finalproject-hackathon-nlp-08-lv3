import os
import re
import sqlite3
import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_upstage import (ChatUpstage, UpstageDocumentParseLoader,
                               UpstageEmbeddings)


def summarize_multiple(data_list):
    """
    객관식 문항 요약 함수
    """

    # 리스트를 딕셔너리로 변환
    data_dict = dict(data_list)

    llm = ChatUpstage()
    enko_translation = ChatUpstage(model="solar-1-mini-translate-enko")
    prompt_template = PromptTemplate.from_template(
        """
        The numbers below are assessments of someone's competence.
        Write a 3-line description based on the scores below. But please exclude the scores from the description.
        ---
        TEXT: {text}
        """
    )
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{text}"),
        ]
    )
    llm_chain = prompt_template | llm | StrOutputParser()

    # Get connection to feedback.db
    conn = sqlite3.connect(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "db/feedback.db")
    )
    cur = conn.cursor()

    # Get keywords from feedback_questions table
    cur.execute(
        "SELECT keyword, question_text FROM feedback_questions WHERE keyword != '' AND question_type = 'single_choice'"
    )
    keyword_pairs = cur.fetchall()
    conn.close()

    # Build the solar_text dynamically
    solar_text_lines = []
    for keyword, question_text in keyword_pairs:
        value = data_dict.get(question_text)
        if value is not None:
            solar_text_lines.append(f"{keyword}: {value}")

    solar_text = "\n    " + "\n    ".join(solar_text_lines)

    # 지수 백오프를 적용하는 while 루프
    wait_time = 1
    while True:
        try:
            response = llm_chain.invoke({"text": solar_text})
        except Exception as e:
            # 에러 메시지에 429 또는 too_many_requests 가 포함되면 백오프 적용
            if "429" in str(e) or "too_many_requests" in str(e):
                time.sleep(wait_time)
                wait_time *= 2
                continue
            else:
                raise
        # 응답에 숫자가 포함되지 않으면 성공으로 간주
        if not re.search(r"\d", response):
            break
    # 번역 체인에도 동일하게 적용 (필요 시)
    wait_time = 1
    translate_chain = chat_prompt | enko_translation | StrOutputParser()
    while True:
        try:
            trans_response = translate_chain.invoke({"text": response})
        except Exception as e:
            if "429" in str(e) or "too_many_requests" in str(e):
                time.sleep(wait_time)
                wait_time *= 2
                continue
            else:
                raise
        break

    return trans_response


def summarize_subjective(data_list):
    """
    주관식 문항 요약 함수, 한 사람의 데이터만 들어옴, key: 질문 번호, value: 답변 리스트
    """

    # 리스트를 딕셔너리로 변환
    data_dict = dict(data_list)

    llm = ChatUpstage()
    prompt_template = PromptTemplate.from_template(
        """
        너는 훌륭한 요약 전문가야.
        아래는 개인이 받은 능력 평가야. 이 내용을 바탕으로 장점 또는 개선할 점을 포함해 1~2줄 요약해줘.
        공식문서 말투로 작성해줘. 답변에 ':'을 넣지 마.
        ---
        TEXT: {text}
        """
    )
    llm_chain = prompt_template | llm | StrOutputParser()

    responses = []

    # 'q_'로 시작하는 키들을 찾아 하나씩 LLM에게 전달
    for idx, key in enumerate(sorted(data_dict.keys())):
        if key.startswith("q_"):
            solar_text = f"characteristic{idx + 1}: {data_dict[key]}"
            wait_time = 1
            while True:
                try:
                    response = llm_chain.invoke({"text": solar_text})
                except Exception as e:
                    if "429" in str(e) or "too_many_requests" in str(e):
                        time.sleep(wait_time)
                        wait_time *= 2
                        continue
                    else:
                        raise
                if not re.search(":", response):
                    break
            responses.append({"question": key, "response": response})

    return responses
