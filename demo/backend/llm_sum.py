import pandas as pd
import re
# import os
import getpass
# import numpy as np
from langchain_upstage import UpstageDocumentParseLoader, ChatUpstage, UpstageEmbeddings
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sklearn.metrics.pairwise import cosine_similarity

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

    solar_text = f"""
    achievement: {data_dict.get('업적')}
    manner: {data_dict.get('태도')}
    ability: {data_dict.get('능력')}
    leadership: {data_dict.get('리더십')}
    cooperation: {data_dict.get('협업')}
    """

    while True:
        response = llm_chain.invoke({"text": solar_text})
        if not re.search(r'\d', response):  # 숫자가 포함되지 않도록 확인
            break
    translate_chain = chat_prompt | enko_translation | StrOutputParser()
    trans_response = translate_chain.invoke({"text": response})
    
    return trans_response

def summarize_subjective(data_list): # 한 사람의 데이터만 들어옴, key: 질문 번호, value: 답변 리스트
    """
    주관식 문항 요약 함수, 추후 pdf.py에 합쳐보고 수정 필요
    """
    
    # 리스트를 딕셔너리로 변환
    data_dict = dict(data_list)
    
    llm = ChatUpstage()
    prompt_template = PromptTemplate.from_template(
        """
        The characteristics below are assessments of someone's competence.
        Write a 2-line description based on the scores below. One for assessment and one for improvement.
        But please exclude the scores from the description.
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
            response = llm_chain.invoke({"text": solar_text})
            responses.append(response)

    return responses


def normalize_tone(data_list):
    """
    말투 정규화 함수, 추후 pdf.py에 합쳐보고 수정 필요
    """
    
    # 리스트를 딕셔너리로 변환
    data_dict = dict(data_list)
    
    llm = ChatUpstage()
    embedding_model = UpstageEmbeddings(model="solar-embedding-1-large")
    
    prompt_template = PromptTemplate.from_template(
        """
        The characteristics below are assessments of someone's competence.
        Please change the tone of the sentences below. And keep the content the same.
        ---
        TEXT: {text}
        """
    )
    
    llm_chain = prompt_template | llm | StrOutputParser()
    
    normalize_dict = {}
    for key in data_dict.keys():
        value_lst = data_dict.get(key)
        tmp_lst = []
        for original in value_lst:
            while True:
                response = llm_chain.invoke({"text": original})
                vector1 = embedding_model.embed_query(original)
                vector2 = embedding_model.embed_query(response)
                # 벡터를 2D 배열로 변환하여 코사인 유사도 계산
                cosine_sim = cosine_similarity([vector1], [vector2])[0][0]
                if abs(cosine_sim) >= 0.8:
                    break
            tmp_lst.append(response)
        normalize_dict[key] = tmp_lst
        
    return normalize_dict
