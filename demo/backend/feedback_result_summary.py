import sqlite3
from qa_db import DB_PATH as FEEDBACK_DB_PATH
from user_db import DB_PATH as USER_DB_PATH
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# API 키 설정
SOLAR_API_KEY = os.getenv("SOLAR_API_KEY")


# Solar API 클라이언트 초기화
client = OpenAI(
    api_key=SOLAR_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

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
    
    response = client.chat.completions.create(
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

def get_user_feedback_summary(username):
    """가장 낮은 점수를 받은 키워드의 주관식 피드백을 분석하여 단점을 도출합니다."""
    feedback_conn = sqlite3.connect(FEEDBACK_DB_PATH)
    user_conn = sqlite3.connect(USER_DB_PATH)
    
    feedback_cur = feedback_conn.cursor()
    user_cur = user_conn.cursor()
    
    # 사용자 정보 가져오기
    user_cur.execute("""
        SELECT name, group_id, rank 
        FROM users 
        WHERE username = ?
    """, (username,))
    user_info = user_cur.fetchone()
    
    if not user_info:
        return f"사용자 {username}을(를) 찾을 수 없습니다."
    
    name, group_id, rank = user_info
    
    # 그룹 정보 가져오기
    user_cur.execute("SELECT group_name FROM groups WHERE id = ?", (group_id,))
    group_name = user_cur.fetchone()[0] if group_id else "소속 그룹 없음"
    
    # 각 키워드별 평균 점수와 팀 평균 점수 계산
    feedback_cur.execute("""
        WITH score_mapping AS (
            SELECT '매우우수' as answer, 5 as score
            UNION SELECT '우수', 4
            UNION SELECT '보통', 3
            UNION SELECT '미흡', 2
            UNION SELECT '매우미흡', 1
        ),
        user_scores AS (
            SELECT 
                q.keyword,
                AVG(CASE 
                    WHEN r.answer_content IN ('매우우수', '우수', '보통', '미흡', '매우미흡')
                    THEN (SELECT score FROM score_mapping WHERE answer = r.answer_content)
                    ELSE NULL
                END) as avg_score
            FROM feedback_results r
            JOIN feedback_questions q ON r.question_id = q.id
            WHERE r.to_username = ?
            GROUP BY q.keyword
        ),
        team_scores AS (
            SELECT 
                q.keyword,
                AVG(CASE 
                    WHEN r.answer_content IN ('매우우수', '우수', '보통', '미흡', '매우미흡')
                    THEN (SELECT score FROM score_mapping WHERE answer = r.answer_content)
                    ELSE NULL
                END) as team_avg_score
            FROM feedback_results r
            JOIN feedback_questions q ON r.question_id = q.id
            WHERE r.to_username != ?
            GROUP BY q.keyword
        )
        SELECT 
            u.keyword,
            u.avg_score,
            t.team_avg_score,
            (t.team_avg_score - u.avg_score) as score_diff
        FROM user_scores u
        JOIN team_scores t ON u.keyword = t.keyword
        ORDER BY u.avg_score ASC, score_diff DESC
    """, (username, username))
    
    keyword_scores = feedback_cur.fetchall()
    
    if not keyword_scores:
        return f"{name}({username})님에 대한 피드백이 아직 없습니다."
    
    # 가장 낮은 점수를 가진 키워드들 중에서 팀 평균과의 차이가 가장 큰 키워드 선택
    min_score = keyword_scores[0][1]  # 최저 점수
    lowest_keywords = [row for row in keyword_scores if row[1] == min_score]
    
    if len(lowest_keywords) > 1:
        # 팀 평균과의 차이가 가장 큰 키워드 선택
        lowest_keyword = max(lowest_keywords, key=lambda x: x[3])[0]
    else:
        lowest_keyword = lowest_keywords[0][0]
    
    # 가장 낮은 점수를 받은 키워드의 주관식 답변 가져오기
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
    
    # 결과 정리
    summary = f"\n=== {name}({username}) 가장 낮은 평가 항목 피드백 요약 ===\n"
    summary += f"소속: {group_name}\n"
    summary += f"직급: {rank}\n"
    summary += f"가장 낮은 평가 항목: {lowest_keyword} (평균 점수: {keyword_scores[0][1]:.2f})\n\n"
    
    if not feedback_results:
        summary += f"{lowest_keyword} 항목에 대한 주관식 피드백이 없습니다.\n"
    else:
        # 피드백을 하나의 문자열로 결합
        all_feedback = f"[{lowest_keyword}]\n"
        for question, answer in feedback_results:
            all_feedback += f"질문: {question}\n"
            all_feedback += f"답변: {answer}\n"
            
        # Solar API로 피드백 분석
        weakness_summary = analyze_feedback_with_solar(all_feedback)
        
        # 결과 출력
        summary += all_feedback + "\n"
        summary += "\n=== AI 분석 결과 ===\n"
        summary += f"주요 개선점: {weakness_summary}\n"
    
    feedback_conn.close()
    user_conn.close()
    
    return summary

def print_all_users_feedback():
    """모든 사용자의 피드백 결과를 출력합니다."""
    user_conn = sqlite3.connect(USER_DB_PATH)
    user_cur = user_conn.cursor()
    
    # admin을 제외한 모든 사용자 가져오기
    user_cur.execute("""
        SELECT username 
        FROM users 
        WHERE role != 'admin'
        ORDER BY group_id, rank DESC
    """)
    
    users = user_cur.fetchall()
    user_conn.close()
    
    for (username,) in users:
        print(get_user_feedback_summary(username))
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    print_all_users_feedback()
