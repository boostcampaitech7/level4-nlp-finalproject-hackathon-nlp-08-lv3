import pandas as pd
import re
from langchain_upstage import UpstageDocumentParseLoader, ChatUpstage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

# def summarize_subjective(subjective_df, llm):
#     """
#     주관식 문항 요약 함수
#     """
#     prompt_template = PromptTemplate.from_template(
#         """
#         Below is someone's strengths and improvements. Summarize the content in 2-3 lines.
#         Keep your speech polite and consistent.
#         ---
#         TEXT: {text}
#         """
#     )
#     chain1 = prompt_template | llm | StrOutputParser()
    
#     results = []
#     for row in subjective_df.itertuples(index=False):
#         solar_text = f"""
#         잘 하는 점: {row.q_26}
#         못 하는 점: {row.q_27}
#         """
#         response = chain1.invoke({"text": solar_text})
#         results.append((row.to_username, response))
    
#     return results
