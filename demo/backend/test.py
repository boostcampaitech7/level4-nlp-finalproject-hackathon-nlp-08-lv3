import pytest
import json
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data == b"Flask backend - from/to username version"

def test_login(client):
    # 성공 케이스
    response = client.post('/api/login', json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'user_id' in data
    assert 'name' in data
    assert 'role' in data

    # 실패 케이스
    response = client.post('/api/login', json={
        "username": "invalid",
        "password": "invalid"
    })
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] == False

def test_create_account(client):
    # 성공 케이스
    response = client.post('/api/create_account', json={
        "username": "newuser",
        "name": "New User",
        "password": "password123",
        "role": "user"
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 중복 아이디 케이스
    response = client.post('/api/create_account', json={
        "username": "newuser",
        "name": "Duplicate User",
        "password": "password123",
        "role": "user"
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] == False

def test_get_users(client):
    response = client.get('/api/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'users' in data
    assert isinstance(data['users'], list)

def test_question_crud(client):
    # 질문 생성
    create_response = client.post('/api/questions', json={
        "keyword": "test",
        "question_text": "Test question?",
        "question_type": "single_choice",
        "options": "yes,no"
    })
    assert create_response.status_code == 200
    create_data = json.loads(create_response.data)
    assert create_data['success'] == True

    # 질문 조회
    get_response = client.get('/api/questions')
    assert get_response.status_code == 200
    get_data = json.loads(get_response.data)
    assert get_data['success'] == True
    assert 'questions' in get_data
    question_id = get_data['questions'][-1]['id']

    # 질문 수정
    update_response = client.put(f'/api/questions/{question_id}', json={
        "keyword": "updated",
        "question_text": "Updated question?",
        "question_type": "single_choice",
        "options": "yes,no"
    })
    assert update_response.status_code == 200
    update_data = json.loads(update_response.data)
    assert update_data['success'] == True

    # 질문 삭제
    delete_response = client.delete(f'/api/questions/{question_id}')
    assert delete_response.status_code == 200
    delete_data = json.loads(delete_response.data)
    assert delete_data['success'] == True

def test_feedback(client):
    # 피드백 제출
    submit_response = client.post('/api/feedback', json={
        "question_id": 1,
        "from_username": "user1",
        "to_username": "user2",
        "answer_content": "Test feedback"
    })
    assert submit_response.status_code == 200
    submit_data = json.loads(submit_response.data)
    assert submit_data['success'] == True

    # 특정 사용자 피드백 조회 (관리자)
    admin_get_response = client.get('/api/feedback/user?username=user2')
    assert admin_get_response.status_code == 200
    admin_get_data = json.loads(admin_get_response.data)
    assert admin_get_data['success'] == True
    assert 'feedbacks' in admin_get_data

    # 내가 받은 피드백 조회
    my_get_response = client.get('/api/feedback/my?username=user2')
    assert my_get_response.status_code == 200
    my_get_data = json.loads(my_get_response.data)
    assert my_get_data['success'] == True
    assert 'feedbacks' in my_get_data

def test_get_question_by_id(client):
    # 존재하는 질문 ID
    response = client.get('/api/questions/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'question' in data

    # 존재하지 않는 질문 ID
    response = client.get('/api/questions/9999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] == False
