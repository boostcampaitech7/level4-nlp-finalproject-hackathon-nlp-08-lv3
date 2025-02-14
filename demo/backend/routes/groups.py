from db.models.user import UserDB
from flask import Blueprint, jsonify, request

groups_bp = Blueprint("groups", __name__)


# 그룹 목록 조회 엔드포인트
@groups_bp.route("/api/groups", methods=["GET"])
def get_groups():
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, group_name, created_at FROM groups")
        groups = [
            {"id": row[0], "group_name": row[1], "created_at": row[2]}
            for row in cur.fetchall()
        ]
        return jsonify({"success": True, "groups": groups}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


# 그룹 생성 엔드포인트
@groups_bp.route("/api/groups/create", methods=["POST"])
def create_group():
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        data = request.get_json()
        group_name = data.get("group_name")
        if not group_name:
            return (
                jsonify({"success": False, "message": "그룹 이름이 필요합니다."}),
                400,
            )

        # 중복 체크
        cur.execute("SELECT id FROM groups WHERE group_name = ?", (group_name,))
        if cur.fetchone():
            return (
                jsonify(
                    {"success": False, "message": "이미 존재하는 그룹 이름입니다."}
                ),
                400,
            )

        # 그룹 생성
        cur.execute("INSERT INTO groups (group_name) VALUES (?)", (group_name,))
        conn.commit()
        return (
            jsonify({"success": True, "message": f"그룹 '{group_name}' 생성 성공"}),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


# 그룹 삭제 엔드포인트
@groups_bp.route("/api/groups/delete/<int:group_id>", methods=["DELETE"])
def delete_group(group_id):
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        if cur.rowcount == 0:
            return (
                jsonify(
                    {"success": False, "message": "해당 그룹이 존재하지 않습니다."}
                ),
                404,
            )
        conn.commit()
        return jsonify({"success": True, "message": "그룹 삭제 성공"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"오류 발생: {str(e)}"}), 500
    finally:
        conn.close()


# 그룹 정보 조회 엔드포인트 (수정 페이지로 전환 시 필요)
@groups_bp.route("/api/groups/<int:group_id>", methods=["GET"])
def get_group(group_id):
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, group_name, created_at FROM groups WHERE id = ?", (group_id,)
        )
        group = cur.fetchone()
        if not group:
            return (
                jsonify({"success": False, "message": "그룹을 찾을 수 없습니다."}),
                404,
            )

        group_data = {"id": group[0], "group_name": group[1], "created_at": group[2]}
        return jsonify({"success": True, "group": group_data}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


# 그룹 업데이트 엔드포인트
@groups_bp.route("/api/groups/update/<int:group_id>", methods=["PUT"])
def update_group(group_id):
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        data = request.get_json()
        group_name = data.get("group_name")
        if not group_name:
            return (
                jsonify({"success": False, "message": "그룹 이름이 필요합니다."}),
                400,
            )

        cur.execute(
            "UPDATE groups SET group_name = ? WHERE id = ?", (group_name, group_id)
        )
        if cur.rowcount == 0:
            return (
                jsonify(
                    {"success": False, "message": "해당 그룹이 존재하지 않습니다."}
                ),
                404,
            )
        conn.commit()
        return (
            jsonify({"success": True, "message": "그룹 정보가 업데이트되었습니다."}),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


# 그룹에 사용자 추가 엔드포인트
@groups_bp.route("/api/groups/users", methods=["POST"])
def add_user_to_group():
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        group_id = data.get("group_id")
        new_rank = data.get("rank")

        if not all([user_id, group_id, new_rank]):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "사용자 ID, 그룹 ID, 직급 정보가 모두 필요합니다.",
                    }
                ),
                400,
            )

        # 이전 정보 조회
        cur.execute(
            """
            SELECT u.name, u.rank, g.group_name 
            FROM users u 
            LEFT JOIN groups g ON u.group_id = g.id 
            WHERE u.id = ?
        """,
            (user_id,),
        )
        prev_info = cur.fetchone()

        # 새로운 그룹 정보 조회
        cur.execute("SELECT group_name FROM groups WHERE id = ?", (group_id,))
        new_group = cur.fetchone()

        # 사용자 정보 업데이트
        cur.execute(
            "UPDATE users SET group_id = ?, rank = ? WHERE id = ?",
            (group_id, new_rank, user_id),
        )

        if cur.rowcount == 0:
            return (
                jsonify(
                    {"success": False, "message": "해당 사용자가 존재하지 않습니다."}
                ),
                404,
            )

        conn.commit()

        # 이전/이후 정보를 포함한 응답
        response_data = {
            "success": True,
            "message": "사용자가 그룹에 추가되었습니다.",
            "previous": {
                "name": prev_info[0],
                "rank": prev_info[1],
                "group_name": prev_info[2] if prev_info[2] else "소속 없음",
            },
            "new": {"group_name": new_group[0], "rank": new_rank},
        }
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


# 그룹에서 사용자 제거 엔드포인트
@groups_bp.route("/api/groups/users/<int:user_id>", methods=["DELETE"])
def remove_user_from_group(user_id):
    conn = UserDB.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET group_id = NULL, rank = NULL WHERE id = ?", (user_id,)
        )
        if cur.rowcount == 0:
            return (
                jsonify(
                    {"success": False, "message": "해당 사용자가 존재하지 않습니다."}
                ),
                404,
            )
        conn.commit()
        return (
            jsonify({"success": True, "message": "사용자가 그룹에서 제거되었습니다."}),
            200,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()
