import os
import sqlite3
import pandas as pd
import numpy as np

# DB 경로 설정
FEEDBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "db/feedback.db")
RESULT_DB_PATH = os.path.join(os.path.dirname(__file__), "db/result.db")

def get_feedback_connection():
    return sqlite3.connect(FEEDBACK_DB_PATH)

def get_result_connection():
    return sqlite3.connect(RESULT_DB_PATH)

def init_result_db():
    # feedback.db에서 unique한 keyword 목록 가져오기
    fb_conn = get_feedback_connection()
    cur = fb_conn.cursor()
    cur.execute("SELECT DISTINCT keyword FROM feedback_questions WHERE keyword != '' AND question_type != 'long_answer'")
    keywords = [row[0] for row in cur.fetchall()]
    
    # unique 질문 ID 가져오기 (주관식)
    cur.execute("SELECT DISTINCT id FROM feedback_questions WHERE question_type = 'long_answer'")
    question_ids = [row[0] for row in cur.fetchall()]
    fb_conn.close()

    # result.db 연결
    conn = get_result_connection()
    cur = conn.cursor()
    # multiple 테이블 생성 - 동적으로 컬럼 생성
    columns = ["id INTEGER PRIMARY KEY", "to_username TEXT NOT NULL"]
    columns.extend([f"{keyword} REAL" for keyword in keywords])
    columns.append("총합 REAL")
    columns.append("등급 TEXT")
    columns.append("created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS multiple (
        {', '.join(columns)}
    )
    '''
    cur.execute(create_table_sql)

    # subjective 테이블 생성 - 동적으로 컬럼 생성 (질문 ID를 사용)
    subj_columns = ["id INTEGER PRIMARY KEY", "to_username TEXT NOT NULL"]
    subj_columns.extend([f"q_{question_id} TEXT" for question_id in question_ids])  # 각 질문의 답변을 저장
    subj_columns.append("created_at DATETIME DEFAULT CURRENT_TIMESTAMP")

    create_subj_table_sql = f'''
    CREATE TABLE IF NOT EXISTS subjective (
        {', '.join(subj_columns)}
    )
    '''
    cur.execute(create_subj_table_sql)

    conn.commit()
    conn.close()
    # unique 질문 ID 가져오기 (주관식)

def process_feedback_data():
    # feedback.db 연결
    fb_conn = get_feedback_connection()
    
    # 키워드 목록 가져오기 - single_choice 타입만 필터링
    cur = fb_conn.cursor()
    cur.execute("SELECT DISTINCT keyword FROM feedback_questions WHERE keyword != '' AND question_type = 'single_choice'")
    keywords = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT DISTINCT id FROM feedback_questions WHERE question_type = 'long_answer'")
    question_ids = [row[0] for row in cur.fetchall()]
    
    # 객관식(single_choice) 데이터 처리
    query = """
    SELECT fr.to_username, fq.keyword, fr.answer_content
    FROM feedback_results fr
    JOIN feedback_questions fq ON fr.question_id = fq.id
    WHERE fq.question_type = 'single_choice'
    """
    
    df = pd.read_sql_query(query, fb_conn)
    
    # 점수 매핑
    score_map = {
        '매우우수': 5,
        '우수': 4,
        '보통': 3,
        '미흡': 2,
        '매우미흡': 1
    }
    
    df['score'] = df['answer_content'].map(score_map)
    
    # 키워드별 평균 계산
    pivot_df = df.pivot_table(
        index='to_username',
        columns='keyword',
        values='score',
        aggfunc='mean'
    ).reset_index()
    
    # to_username으로 정렬
    pivot_df = pivot_df.sort_values('to_username')
    
    # 수치형 컬럼 소수점 2자리로 반올림
    for column in keywords:
        pivot_df[column] = pivot_df[column].round(2)
    
    # '총합' 열 추가
    pivot_df['총합'] = pivot_df[keywords].sum(axis=1)
    
    # 'average' 행 추가
    average_row = pivot_df[keywords].mean().round(2).to_dict()
    average_row['to_username'] = 'average'
    average_row['총합'] = pivot_df['총합'].mean().round(2)
    pivot_df = pivot_df._append(average_row, ignore_index=True)
    
    # '등급' 열 추가
    def map_grade(pivot_df, column='총합'):
        # 값 기준으로 내림차순 정렬
        sorted_values = pivot_df[pivot_df['to_username'] != 'average'][column].sort_values(ascending=False)
        total_count = len(sorted_values)

        # 등급 비율
        ratios = [0.1, 0.2, 0.3, 0.3, 0.1]
        grades = ['S', 'A', 'B', 'C', 'D']

        # 각 등급의 경계값 계산 (0~1 범위로 제한)
        thresholds = [sorted_values.quantile(max(0, min(1, 1 - sum(ratios[:i+1])))) for i in range(len(ratios))]

        # 등급 매핑
        def assign_grade(value):
            for grade, threshold in zip(grades, thresholds):
                if value >= threshold:
                    return grade
            return 'D'  # 가장 낮은 등급

        return pivot_df[column].map(assign_grade)

    pivot_df.loc[pivot_df['to_username'] != 'average', '등급'] = map_grade(pivot_df)
    
    # 결과 DB에 저장
    result_conn = get_result_connection()
    
    # multiple 테이블 데이터 저장
    for _, row in pivot_df.iterrows():
        cur = result_conn.cursor()
        placeholders = ', '.join(['?' for _ in range(len(keywords) + 3)])  # '총합'과 '등급' 추가
        columns = ['to_username'] + keywords + ['총합', '등급']
        
        values = [row['to_username']] + [row.get(keyword, 0) for keyword in keywords] + [row['총합'], row.get('등급', '')]
        
        insert_sql = f"""
            INSERT INTO multiple (
                {', '.join(columns)}
            ) VALUES ({placeholders})
        """
        cur.execute(insert_sql, values)
    
    # 주관식 데이터 처리
    subj_query = """
    SELECT fr.to_username, fq.id AS question_id, fr.answer_content
    FROM feedback_results fr
    JOIN feedback_questions fq ON fr.question_id = fq.id
    WHERE fr.answer_content NOT IN ('매우우수', '우수', '보통', '미흡', '매우미흡') AND fq.question_type == 'long_answer'
    """
    
    subj_df = pd.read_sql_query(subj_query, fb_conn)
    
    # subjective 테이블 데이터 저장
    for username in subj_df['to_username'].unique():
        feedbacks = subj_df[subj_df['to_username'] == username]
        
        # 각 질문 ID에 대해 답변 리스트 생성
        feedback_dict = {f"q_{question_id}": feedbacks[feedbacks['question_id'] == question_id]['answer_content'].tolist() for question_id in question_ids}
        
        cur = result_conn.cursor()
        # 데이터 삽입
        insert_values = [username] + [str(feedback_dict.get(f"q_{question_id}", [])) for question_id in question_ids]
        cur.execute(f"""
            INSERT INTO subjective (to_username, {', '.join([f'q_{question_id}' for question_id in question_ids])})
            VALUES (?, {', '.join(['?' for _ in range(len(question_ids))])})
        """, insert_values)
    
    result_conn.commit()
    result_conn.close()
    fb_conn.close()


if __name__ == "__main__":
    init_result_db()
    process_feedback_data()