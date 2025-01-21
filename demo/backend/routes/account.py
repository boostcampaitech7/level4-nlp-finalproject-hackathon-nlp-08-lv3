from flask import Blueprint, request, jsonify
from user_db import get_connection

account_bp = Blueprint("account", __name__)

# 계정 생성
@account_bp.route("/api/create_account", methods=["POST"])
def create_account():
    data = request.json
    username = data.get("username")
    name = data.get("name")
    password = data.get("password")
    role = data.get("role")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
    if cur.fetchone()[0] > 0:
        conn.close()
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."}), 400

    cur.execute("""
        INSERT INTO users (username, name, password, role)
        VALUES (?, ?, ?, ?)
    """, (username, name, password, role))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "계정 생성 완료"})


# 사용자 목록 조회
@account_bp.route("/api/users", methods=["GET"])

# def get_users():
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute("SELECT id, username, name, role FROM users ORDER BY id ASC")
#     rows = cur.fetchall()
#     conn.close()

#     users = []
#     for r in rows:
#         users.append({
#             "id": r[0],
#             "username": r[1],
#             "name": r[2],
#             "role": r[3]
#         })
#     return jsonify({"success": True, "users": users})

def get_users():
    conn = get_connection()
    cur = conn.cursor()
    ### 그룹 수정 시작
    try:
        # LEFT JOIN으로 user_groups 테이블과 연결하여 그룹 정보도 함께 조회
        cur.execute("""
            SELECT u.id, u.username, u.name, u.role, ug.group_id 
            FROM users u 
            LEFT JOIN user_groups ug ON u.id = ug.user_id 
            ORDER BY u.id ASC
        """)
        rows = cur.fetchall()
        
        users = []
        for r in rows:
            users.append({
                "id": r[0],
                "username": r[1],
                "name": r[2],
                "role": r[3],
                "group_id": r[4]  # 그룹 정보 추가
            })
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
    ### 그룹 수정 끝