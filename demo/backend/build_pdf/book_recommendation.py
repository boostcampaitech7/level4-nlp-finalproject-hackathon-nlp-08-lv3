import os
import pickle
import sqlite3
import time

import numpy as np
from db.models.qa import DB_PATH as FEEDBACK_DB_PATH
from dotenv import load_dotenv
from load_book_chunk import BOOK_CHUNK_CACHE
from openai import OpenAI

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
)

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
solar_client = OpenAI(
    api_key=UPSTAGE_API_KEY, base_url="https://api.upstage.ai/v1/solar"
)

BOOK_CHUNK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "book_chunk")


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# --- API 호출 재시도 helper 함수 ---
def retry_api_call(api_func, *args, max_attempts=3, **kwargs):
    """API 호출 시 RateLimit (429) 에러에 대해 지수 백오프를 적용하여 재시도"""
    attempt = 0
    wait_time = 1
    last_exception = None
    while attempt < max_attempts:
        attempt += 1
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            # 메시지나 에러 코드에 '429' 또는 'too_many_requests'가 포함되면 재시도
            if "429" in str(e) or "too_many_requests" in str(e):
                time.sleep(wait_time)
                wait_time *= 2
            else:
                raise
    raise last_exception


def analyze_feedback_with_solar(feedback_text):
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
    response = retry_api_call(
        solar_client.chat.completions.create,
        model="solar-pro",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    return response.choices[0].message.content


def find_lowest_keyword(scores, team_average):
    if not scores or not team_average:
        return None
    score_dict = {item[0]: float(item[1]) for item in scores}
    avg_dict = {item[0]: float(item[1]) for item in team_average}
    min_score = min(score_dict.values())
    lowest_keywords = [k for k, v in score_dict.items() if v == min_score]
    if len(lowest_keywords) == 1:
        return lowest_keywords[0]
    max_diff = float("-inf")
    selected_keyword = lowest_keywords[0]
    for keyword in lowest_keywords:
        diff = avg_dict[keyword] - score_dict[keyword]
        if diff > max_diff:
            max_diff = diff
            selected_keyword = keyword
    return selected_keyword


def summarize_book_content(content):
    try:
        prompt = f"""
아래의 책의 내용을 읽고 핵심 내용을 요약해주세요

{content}

요약할 때 다음 사항을 지켜주세요:
1. 책의 핵심 주제나 메시지를 포함할 것
2. 간결하고 명확하게 작성할 것
3. 공백 포함 최대 300자 내로 요약할 것
"""
        response = retry_api_call(
            solar_client.chat.completions.create,
            model="solar-pro",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            timeout=10,
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"책 내용 요약 중 오류 발생: {str(e)}")
        return content[:300] + "..."


def get_book_recommendation(username, lowest_keyword):
    try:
        # 피드백 결과 가져오기 (feedback.db 사용)
        feedback_conn = sqlite3.connect(FEEDBACK_DB_PATH)
        feedback_cur = feedback_conn.cursor()
        feedback_cur.execute(
            """
            SELECT q.question_text, r.answer_content
            FROM feedback_results r
            JOIN feedback_questions q ON r.question_id = q.id
            WHERE r.to_username = ? 
            AND q.keyword = ?
            AND r.answer_content NOT IN ('매우우수', '우수', '보통', '미흡', '매우미흡')
            ORDER BY r.created_at
        """,
            (username, lowest_keyword),
        )
        feedback_results = feedback_cur.fetchall()
        if not feedback_results:
            print(f"[{username}] 주관식 피드백이 없습니다.")
            return None
        all_feedback = f"[{lowest_keyword}]\n"
        for question, answer in feedback_results:
            all_feedback += f"질문: {question}\n"
            all_feedback += f"답변: {answer}\n"
        detail_query = analyze_feedback_with_solar(all_feedback)
        print(f"[{username}] AI 분석 결과: {detail_query}")
        print(f"\n[{username}] '{lowest_keyword}' 키워드에 대한 도서 검색 시작...")
        try:
            query_embedding_response = retry_api_call(
                solar_client.embeddings.create,
                input=detail_query,
                model="embedding-query",
                timeout=5,
            )
            query_embedding = query_embedding_response.data[0].embedding
        except Exception as e:
            print(f"[{username}] 쿼리 임베딩 생성 실패: {str(e)}")
            return None

        best_books = []
        similarities = []

        print(f"[{username}] 책 청크 캐시에서 검색 중...")
        # BOOK_CHUNK_CACHE (load_book_chunk.py에서 미리 로드됨)을 사용하여 디스크 I/O를 줄임
        for chunk_file, chunk_data in BOOK_CHUNK_CACHE.items():
            if not isinstance(chunk_data, dict):
                continue
            for book_data in chunk_data.values():
                book_embedding = book_data.get("embedding")
                if book_embedding:
                    similarity = cosine_similarity(query_embedding, book_embedding)
                    if len(best_books) < 3:
                        best_books.append(book_data)
                        similarities.append(similarity)
                        # 정렬: 상위 유사도 순으로 유지
                        for i in range(len(similarities) - 1):
                            if similarities[i] < similarities[i + 1]:
                                similarities[i], similarities[i + 1] = (
                                    similarities[i + 1],
                                    similarities[i],
                                )
                                best_books[i], best_books[i + 1] = (
                                    best_books[i + 1],
                                    best_books[i],
                                )
                    elif similarity > similarities[-1]:
                        best_books[-1] = book_data
                        similarities[-1] = similarity
                        for i in range(len(similarities) - 1):
                            if similarities[i] < similarities[i + 1]:
                                similarities[i], similarities[i + 1] = (
                                    similarities[i + 1],
                                    similarities[i],
                                )
                                best_books[i], best_books[i + 1] = (
                                    best_books[i + 1],
                                    best_books[i],
                                )

        if not best_books:
            print(f"[{username}] 적합한 도서를 찾지 못했습니다.")
            return None

        recommendations = []
        for i, (book, similarity) in enumerate(zip(best_books, similarities)):
            print(f"\n[{username}] {i+1}번째 추천 도서:")
            print(f"제목: {book['title']}")
            print(f"유사도: {similarity:.4f}")
            content_summary = summarize_book_content(book["contents"])
            recommendations.append(
                {
                    "title": book["title"],
                    "authors": (
                        ", ".join(book["authors"])
                        if isinstance(book["authors"], list)
                        else book["authors"]
                    ),
                    "contents": content_summary,
                    "thumbnail": book.get("thumbnail"),
                    "query": detail_query,
                }
            )
        feedback_conn.close()
        return recommendations
    except Exception as e:
        print(f"[{username}] 도서 추천 중 오류 발생: {str(e)}")
        return None
