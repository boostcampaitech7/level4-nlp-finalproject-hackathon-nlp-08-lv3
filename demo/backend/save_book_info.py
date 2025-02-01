import requests
from openai import OpenAI
import numpy as np
import pickle
from datetime import datetime
import os
from tqdm import tqdm
import time
from dotenv import load_dotenv

load_dotenv()

# API 키 설정
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
SOLAR_API_KEY = os.getenv("SOLAR_API_KEY")

# Solar Embeddings 클라이언트 설정
solar_client = OpenAI(
    api_key=SOLAR_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# 검색할 키워드 리스트 정의
search_keywords = [
    '업적', '능력', '협업심', '리더십', '태도', '경영', '자기계발', 
    '성공', '비즈니스', '인문', '소설', '과학', '예술', '역사', 
    '철학', '심리', '교육', '문화', '정치', '경제'
]

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def fetch_books_by_keyword(keyword, total_count=300):
    """키워드로 도서를 검색하는 함수"""
    url = "https://dapi.kakao.com/v3/search/book"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    
    all_books = []
    page = 1
    
    while len(all_books) < total_count:
        params = {
            "query": keyword,
            "size": min(50, total_count - len(all_books)),
            "page": page,
            "target": "title"
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break
            
        result = response.json()
        books = result.get("documents", [])
        if not books:
            break
            
        all_books.extend(books)
        page += 1
    
    return all_books

def create_embedding(text, timeout=5):
    """텍스트의 임베딩을 생성하는 함수 (제한시간 5초)"""
    start_time = time.time()
    
    try:
        embedding_response = solar_client.embeddings.create(
            input=text,
            model="embedding-passage"
        )
        
        processing_time = time.time() - start_time
        if processing_time > timeout:
            print(f"\n경고: 임베딩 처리 시간 초과 ({processing_time:.2f}초)")
            return None
            
        return embedding_response.data[0].embedding
        
    except Exception as e:
        print(f"\n임베딩 생성 중 오류 발생: {str(e)}")
        return None

def load_existing_books():
    """기존에 저장된 도서 데이터를 로드하는 함수"""
    try:
        with open('all_books.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {}

def save_books(books_data):
    """도서 데이터를 저장하는 함수"""
    with open('all_books.pkl', 'wb') as f:
        pickle.dump(books_data, f)

def load_progress():
    """진행 상황을 로드하는 함수"""
    try:
        with open('progress.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return {
            'completed_keywords': set(),  # 처리 완료된 키워드 집합
            'last_processed_chunk': None,  # 마지막으로 처리된 청크 ID
            'completed_chunks': set()  # 처리 완료된 청크 집합
        }

def save_progress(progress):
    """진행 상황을 저장하는 함수"""
    with open('progress.pkl', 'wb') as f:
        pickle.dump(progress, f)

def process_and_save_books_in_chunks():
    """청크 단위로 도서 정보를 처리하는 함수"""
    chunk_size = 1000
    processed_isbns = set()
    total_processed = 0
    
    # 저장 경로 설정
    save_dir = "/data/ephemeral/home/juhyun/level4-nlp-finalproject-hackathon-nlp-08-lv3/demo/backend/book_chunk"
    os.makedirs(save_dir, exist_ok=True)
    
    print("\n=== 도서 정보 수집 시작 ===")
    print(f"청크 크기: {chunk_size}")
    
    # 기존 처리된 ISBN 로드 부분 수정
    print("\n1. 기존 처리된 도서 정보 로드 중...")
    for chunk_file in tqdm(os.listdir(save_dir), desc="청크 파일 검사"):
        if chunk_file.startswith('books_chunk_') and chunk_file.endswith('.pkl'):
            try:
                with open(os.path.join(save_dir, chunk_file), 'rb') as f:
                    chunk_data = pickle.load(f)
                    processed_isbns.update(chunk_data.keys())
            except Exception as e:
                print(f"경고: 청크 파일 '{chunk_file}' 로드 중 오류 발생: {str(e)}")
    
    print(f"- 기존 처리된 도서 수: {len(processed_isbns)}개")
    
    # 중복 키워드 제거
    unique_keywords = list(dict.fromkeys(search_keywords))
    print(f"\n2. 처리할 키워드: {len(unique_keywords)}개")
    print(f"- 키워드 목록: {', '.join(unique_keywords)}")
    
    try:
        chunk_number = len([f for f in os.listdir(save_dir) if f.startswith('books_chunk_')])
        print(f"\n3. 청크 처리 시작 (현재 청크 번호: {chunk_number})")
        
        for keyword_idx, keyword in enumerate(unique_keywords, 1):
            print(f"\n=== 키워드 {keyword_idx}/{len(unique_keywords)}: '{keyword}' 처리 중 ===")
            current_chunk = {}
            
            # 키워드로 도서 검색
            books = fetch_books_by_keyword(keyword)
            print(f"- 검색된 도서: {len(books)}개")
            
            new_books = 0
            with tqdm(books, desc="도서 처리", unit="권") as pbar:
                for book in pbar:
                    isbn = book.get('isbn', '').split(" ")[0]
                    if not isbn or isbn in processed_isbns:
                        continue
                        
                    current_chunk[isbn] = book
                    new_books += 1
                    
                    # 청크 크기에 도달하면 처리 및 저장
                    if len(current_chunk) >= chunk_size:
                        print("\n- 청크 처리 중...")
                        processed_chunk = process_chunk(current_chunk.values())
                        if processed_chunk:
                            save_chunk(processed_chunk, chunk_number)
                            processed_isbns.update(processed_chunk.keys())
                            total_processed += len(processed_chunk)
                            chunk_number += 1
                        current_chunk = {}
            
            # 남은 데이터 처리
            if current_chunk:
                print("\n- 남은 도서 처리 중...")
                processed_chunk = process_chunk(current_chunk.values())
                if processed_chunk:
                    save_chunk(processed_chunk, chunk_number)
                    processed_isbns.update(processed_chunk.keys())
                    total_processed += len(processed_chunk)
                    chunk_number += 1
            
            print(f"\n- 키워드 '{keyword}' 처리 완료")
            print(f"- 새로 추가된 도서: {new_books}개")
            
    except KeyboardInterrupt:
        print("\n\n=== 사용자에 의해 중단됨 ===")
        if current_chunk:
            print("- 마지막 청크 저장 중...")
            processed_chunk = process_chunk(current_chunk.values())
            if processed_chunk:
                save_chunk(processed_chunk, chunk_number)
                total_processed += len(processed_chunk)
    
    except Exception as e:
        print(f"\n\n=== 오류 발생 ===")
        print(f"오류 내용: {str(e)}")
        if current_chunk:
            print("- 마지막 청크 저장 중...")
            processed_chunk = process_chunk(current_chunk.values())
            if processed_chunk:
                save_chunk(processed_chunk, chunk_number)
                total_processed += len(processed_chunk)
    
    finally:
        print("\n=== 처리 완료 ===")
        print(f"- 총 처리된 새로운 도서: {total_processed}개")
        print(f"- 전체 저장된 도서: {len(processed_isbns)}개")
        print(f"- 생성된 청크 파일 수: {chunk_number}개")

def find_similar_books(query_text, top_k=5):
    """쿼리와 가장 유사한 도서를 찾는 함수"""
    all_books_data = load_existing_books()
    
    query_embedding = create_embedding(query_text)
    if not query_embedding:
        return []
    
    similarities = []
    for isbn, book_data in all_books_data.items():
        similarity = np.dot(query_embedding, book_data['embedding']) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(book_data['embedding'])
        )
        similarities.append((similarity, book_data))
    
    return sorted(similarities, key=lambda x: x[0], reverse=True)[:top_k]

def process_chunk(books):
    """도서 데이터를 처리하고 임베딩을 생성하는 함수"""
    chunk_data = {}
    total_books = len(books)
    success_count = 0
    skip_count = 0
    timeout_count = 0
    
    for book in tqdm(books, desc="청크 처리 중", unit="권"):
        process_start_time = time.time()
        
        isbn = book.get("isbn", "").split(" ")[0]
        if not isbn:
            skip_count += 1
            continue
            
        contents = book.get("contents", "")
        if not contents:
            skip_count += 1
            continue
            
        # 임베딩 생성 시간 제한 적용
        embedding = create_embedding(contents, timeout=5)
        if embedding:
            chunk_data[isbn] = {
                'title': book.get('title'),
                'authors': book.get('authors'),
                'publisher': book.get('publisher'),
                'contents': contents,
                'thumbnail': book.get('thumbnail'),
                'embedding': embedding,
                'isbn': isbn,
                'timestamp': datetime.now().isoformat(),
                'processing_time': time.time() - process_start_time
            }
            success_count += 1
        else:
            timeout_count += 1
            tqdm.write(f"\n도서 '{book.get('title')}' 임베딩 생성 실패 - 건너뛰기")
    
    # 처리 결과 출력
    print(f"\n청크 처리 결과:")
    print(f"- 전체 도서: {total_books}권")
    print(f"- 성공: {success_count}권")
    print(f"- 건너뛰기: {skip_count}권")
    print(f"- 시간초과: {timeout_count}권")
    
    return chunk_data

def save_chunk(books_chunk, chunk_number):
    """청크 데이터를 파일로 저장하는 함수"""
    if books_chunk:  # 청크에 데이터가 있는 경우에만 저장
        save_dir = "/data/ephemeral/home/juhyun/level4-nlp-finalproject-hackathon-nlp-08-lv3/demo/backend/book_chunk"
        chunk_filename = os.path.join(save_dir, f'books_chunk_{chunk_number}.pkl')
        with open(chunk_filename, 'wb') as f:
            pickle.dump(books_chunk, f)
        print(f"청크 {chunk_number} 저장 완료 (도서 {len(books_chunk)}개)")

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"처리 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    process_and_save_books_in_chunks()
    
    end_time = datetime.now()
    processing_time = end_time - start_time
    print(f"\n총 처리 시간: {processing_time}")
    
    # 유사 도서 검색 예시
    # query = "리더십과 팀워크의 중요성"
    # similar_books = find_similar_books(query)
    # for similarity, book in similar_books:
    #     print(f"\n유사도: {similarity:.4f}")
    #     print(f"제목: {book['title']}")
    #     print(f"저자: {', '.join(book['authors'])}")