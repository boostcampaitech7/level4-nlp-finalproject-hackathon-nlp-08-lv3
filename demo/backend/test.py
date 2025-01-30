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
        "role": "user",
        "email": "newuser@example.com"
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 중복 아이디 케이스
    response = client.post('/api/create_account', json={
        "username": "newuser",
        "name": "Duplicate User",
        "password": "password123",
        "role": "user",
        "email": "duplicate@example.com"
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] == False

    # 중복 이메일 케이스
    response = client.post('/api/create_account', json={
        "username": "anotheruser",
        "name": "Another User",
        "password": "password123",
        "role": "user",
        "email": "newuser@example.com"
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

def test_bulk_feedback_submission(client):
    # 유효한 피드백 데이터
    valid_feedback = [
        {
            "question_id": 1,
            "from_username": "user1",
            "to_username": "user2",
            "answer_content": "Feedback 1"
        },
        {
            "question_id": 2,
            "from_username": "user1",
            "to_username": "user3",
            "answer_content": "Feedback 2"
        }
    ]
    response = client.post('/api/feedback/bulk', json=valid_feedback)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 유효하지 않은 피드백 데이터 (필드 누락)
    invalid_feedback = [
        {
            "question_id": 1,
            "from_username": "user1",
            "to_username": "user2"
            # answer_content 누락
        }
    ]
    response = client.post('/api/feedback/bulk', json=invalid_feedback)
    assert response.status_code == 500
    data = json.loads(response.data)
    assert data['success'] == False

def test_check_feedback(client):
    # 피드백 존재 확인
    response = client.get('/api/feedback/check?from_username=user1&to_username=user2')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['already_submitted'] == True

    # 피드백 미존재 확인
    response = client.get('/api/feedback/check?from_username=user1&to_username=user999')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['already_submitted'] == False

def test_group_operations(client):
    # 그룹 생성
    response = client.post('/api/groups/create', json={"group_name": "Test Group"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 그룹 목록 조회
    response = client.get('/api/groups')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'groups' in data

    # 그룹 정보 조회
    group_id = data['groups'][-1]['id']
    response = client.get(f'/api/groups/{group_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 그룹 업데이트
    response = client.put(f'/api/groups/update/{group_id}', json={"group_name": "Updated Group"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True

    # 그룹 삭제
    response = client.delete(f'/api/groups/delete/{group_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
