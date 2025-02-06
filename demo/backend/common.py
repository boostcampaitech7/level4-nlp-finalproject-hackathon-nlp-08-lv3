import os
import pickle
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(__file__)
BOOK_CHUNK_DIR = os.path.join(BASE_DIR, "book_chunk")
BOOK_CHUNK_CACHE = {}

def load_chunk_file(chunk_file):
    try:
        with open(os.path.join(BOOK_CHUNK_DIR, chunk_file), 'rb') as f:
            return chunk_file, pickle.load(f)
    except Exception as e:
        return chunk_file, None

def load_all_book_chunks():
    """
    BOOK_CHUNK_CACHE를 디스크에서 한 번 읽어 메모리에 저장합니다.
    """
    global BOOK_CHUNK_CACHE
    with os.scandir(BOOK_CHUNK_DIR) as it:
        chunk_files = [
            entry.name for entry in it 
            if entry.is_file() and entry.name.startswith('books_chunk_') and entry.name.endswith('.pkl')
        ]
    with ThreadPoolExecutor() as executor:
        results = executor.map(load_chunk_file, chunk_files)
    for filename, data in results:
        if data is not None:
            BOOK_CHUNK_CACHE[filename] = data
    return BOOK_CHUNK_CACHE
