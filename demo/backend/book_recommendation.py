from openai import OpenAI
import sqlite3
import os
import pickle
import numpy as np
from qa_db import DB_PATH as FEEDBACK_DB_PATH
from dotenv import load_dotenv

load_dotenv()

# Solar API 설정
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
solar_client = OpenAI(
    api_key=UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

BOOK_CHUNK_DIR = os.path.join(os.path.dirname(__file__), "book_chunk")

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def analyze_feedback_with_solar(feedback_text):
    """Solar API를 사용하여 피드백을 분석하고 도서 추천을 위한 쿼리 문장을 생성합니다."""
    prompt = f"""
다음은 한 직원이 가장 낮은 평가를 받은 항목에 대한 동료들의 피드백입니다:
{feedback_text}

위 피드백들을 분석하여 이 직원의 가장 큰 단점이나 개선이 필요한 부분을 다음과 같은 형식으로 작성해주세요:
"직장 내에서 ~하는 능력이 부족한 사람을 위한 책"

예시:
- "직장 내에서 효과적으로 의사소통하는 능력이 부족한 사람을 위한 책"
- "직장 내에서 시간 관리와 업무 우선순위 설정 능력이 부족한 사람을 위한 책"
- "직장 내에서 팀원들과 협업하는 능력이 부족한 사람을 위한 책"
"""
    
    response = solar_client.chat.completions.create(
        model="solar-pro",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        stream=False
    )
    
    return response.choices[0].message.content


def find_lowest_keyword(scores, team_average):
    """점수 리스트에서 가장 낮은 점수의 키워드를 반환
    동일한 최저 점수가 있을 경우 팀 평균과의 차이가 가장 큰 키워드를 반환"""
    if not scores or not team_average:
        return None
        
    # 점수와 팀 평균을 딕셔너리로 변환
    score_dict = {item[0]: float(item[1]) for item in scores}
    avg_dict = {item[0]: float(item[1]) for item in team_average}
    
    # 가장 낮은 점수 찾기
    min_score = min(score_dict.values())
    
    # 가장 낮은 점수를 가진 키워드들 찾기
    lowest_keywords = [k for k, v in score_dict.items() if v == min_score]
    
    if len(lowest_keywords) == 1:
        return lowest_keywords[0]
    
    # 여러 개의 최저 점수가 있는 경우, 팀 평균과의 차이가 가장 큰 키워드 선택
    max_diff = float('-inf')
    selected_keyword = lowest_keywords[0]
    
    for keyword in lowest_keywords:
        diff = avg_dict[keyword] - score_dict[keyword]
        if diff > max_diff:
            max_diff = diff
            selected_keyword = keyword
            
    return selected_keyword

def summarize_book_content(content):
    """Solar Chat API를 사용하여 책 내용을 2-3문장으로 요약"""
    try:
        prompt = f"""
다음은 책의 내용입니다. 2-3문장으로 핵심 내용을 요약해주세요:

{content}

요약할 때 다음 사항을 지켜주세요:
1. 책의 핵심 주제나 메시지를 포함할 것
2. 간결하고 명확하게 작성할 것
3. 2-3문장으로 제한할 것
"""

        response = solar_client.chat.completions.create(
            model="solar-pro",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=False,
            timeout=10
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"책 내용 요약 중 오류 발생: {str(e)}")
        return content[:300] + "..."  # 오류 발생 시 기존 방식으로 처리

def get_book_recommendation(username, lowest_keyword):
    """특정 키워드에 대한 도서 추천을 반환"""
    try:
        # 피드백 결과 가져오기 (feedback.db 사용)
        feedback_conn = sqlite3.connect(FEEDBACK_DB_PATH)
        feedback_cur = feedback_conn.cursor()
        
        # 가장 낮은 점수를 받은 키워드의 주관식 답변 가져오기 (원래 키워드 그대로 사용)
        feedback_cur.execute("""
            SELECT q.question_text, r.answer_content
            FROM feedback_results r
            JOIN feedback_questions q ON r.question_id = q.id
            WHERE r.to_username = ? 
            AND q.keyword = ?
            AND r.answer_content NOT IN ('매우우수', '우수', '보통', '미흡', '매우미흡')
            ORDER BY r.created_at
        """, (username, lowest_keyword))
        
        feedback_results = feedback_cur.fetchall()
        
        if not feedback_results:
            print(f"[{username}] 주관식 피드백이 없습니다.")
            return None
            
        # 피드백을 하나의 문자열로 결합
        all_feedback = f"[{lowest_keyword}]\n"
        for question, answer in feedback_results:
            all_feedback += f"질문: {question}\n"
            all_feedback += f"답변: {answer}\n"
            
        # Solar API로 피드백 분석하여 도서 검색 쿼리 생성
        detail_query = analyze_feedback_with_solar(all_feedback)
        print(f"[{username}] AI 분석 결과: {detail_query}")
        print(f"\n[{username}] '{lowest_keyword}' 키워드에 대한 도서 검색 시작...")
        
        # Solar 임베딩 생성
        try:
            query_embedding_response = solar_client.embeddings.create(
                input=detail_query,
                model="embedding-query",
                timeout=5
            )
            query_embedding = query_embedding_response.data[0].embedding
        except Exception as e:
            print(f"[{username}] 쿼리 임베딩 생성 실패: {str(e)}")
            return None
            
        # 수정된 부분: BOOK_CHUNK_DIR 상수 사용
        best_similarity = -1
        best_book = None
        
        print(f"[{username}] book_chunk 파일 검색 중...")
        
        for chunk_file in os.listdir(BOOK_CHUNK_DIR):
            if chunk_file.startswith('books_chunk_') and chunk_file.endswith('.pkl'):
                try:
                    with open(os.path.join(BOOK_CHUNK_DIR, chunk_file), 'rb') as f:
                        chunk_data = pickle.load(f)
                        
                        # 각 책의 임베딩과 유사도 계산
                        for book_data in chunk_data.values():
                            book_embedding = book_data.get('embedding')
                            if book_embedding:
                                similarity = cosine_similarity(query_embedding, book_embedding)
                                if similarity > best_similarity:
                                    best_similarity = similarity
                                    best_book = book_data
                                    
                except Exception as e:
                    print(f"[{username}] 청크 파일 '{chunk_file}' 처리 중 오류: {str(e)}")
                    continue
        
        if not best_book:
            print(f"[{username}] 적합한 도서를 찾지 못했습니다.")
            return None
            
        print(f"\n[{username}] 최적의 도서를 찾았습니다:")
        print(f"제목: {best_book['title']}")
        print(f"유사도: {best_similarity:.4f}")
        
        # 수정된 부분: 책 내용 요약 추가
        if best_book:
            content_summary = summarize_book_content(best_book['contents'])
            print(f"\n[{username}] 책 내용 요약 완료")
            
            recommendation = {
                'title': best_book['title'],
                'authors': ', '.join(best_book['authors']) if isinstance(best_book['authors'], list) else best_book['authors'],
                'contents': content_summary,  # 요약된 내용으로 변경
                'thumbnail': best_book.get('thumbnail'),
                'query': detail_query
            }
            
            feedback_conn.close()
            return recommendation
        
    except Exception as e:
        print(f"[{username}] 도서 추천 중 오류 발생: {str(e)}")
        return None