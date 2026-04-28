from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from agora_token_builder import RtcTokenBuilder
import os
import sys
import time

import main
from config.firebase_admin import firebase_admin_service
from manage import app

sys.path.append(os.path.dirname(__file__))


def extract_error_message(result):
    message = result.get("message")
    if isinstance(message, str) and message.strip():
        return message

    error = result.get("error")
    if isinstance(error, str) and error.strip():
        return error

    error_code = result.get("errorCode")
    if isinstance(error_code, str) and error_code.strip():
        return error_code

    return "Loi he thong"


def build_session_user(data):
    if not isinstance(data, dict):
        return {}

    return {
        "studentId": data.get("studentId"),
        "name": data.get("name"),
        "username": data.get("username"),
        "password": data.get("password"),
        "domain": data.get("domain"),
        "major": data.get("major"),
        "class_name": data.get("class_name"),
        "school_name": data.get("school_name"),
        "avatar": data.get("avatar"),
    }


def get_session_user():
    return session.get("user")


def require_session_user_json():
    user = get_session_user()
    if not user:
        return None, (jsonify({"success": False, "error": "Unauthorized"}), 401)
    return user, None


@app.route("/")
def index():
    return redirect(url_for("login_form"))


@app.route("/login", methods=["GET"])
def login_form():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    username = request.form.get("username")
    password = request.form.get("password")
    domain = request.form.get("domain")

    result = main.run_case(username, password, domain, "login")

    if result.get("error"):
        if request.is_json:
            return jsonify({"success": False, "error": extract_error_message(result)}), 401

        flash(extract_error_message(result), "error")
        return redirect(url_for("login_form"))

    session["user"] = build_session_user(result.get("data"))
    session.modified = True
    return redirect("/dashboard")


@app.route("/app-login", methods=["POST"])
def login_app_submit():
    if not request.is_json:
      return jsonify({"success": False, "error": "Invalid request"}), 400

    req_data = request.get_json()
    username = req_data.get("username")
    password = req_data.get("password")
    domain = req_data.get("domain")
    lat = req_data.get("lat")
    lng = req_data.get("lng")

    result = main.run_case(username, password, domain, "schedule")

    if result.get("error"):
        error_message = extract_error_message(result)
        return jsonify(
            {
                "success": False,
                "errorCode": result.get("errorCode", "UNKNOWN"),
                "error": error_message,
                "message": error_message,
            }
        ), 400

    user_info = result.get("user")
    if not user_info:
        return jsonify(
            {
                "success": False,
                "error": "Khong lay duoc thong tin user",
            }
        ), 500

    session["user"] = build_session_user(
        {
            **user_info,
            "username": username,
            "password": password,
            "domain": domain,
        }
    )
    session.modified = True

    user_payload = {
        "studentId": user_info.get("studentId"),
        "name": user_info.get("name"),
        "className": user_info.get("class_name"),
        "schoolName": user_info.get("school_name"),
        "major": user_info.get("major"),
        "avatar": user_info.get("avatar") or "https://i.pravatar.cc/400?img=2",
        "lat": lat,
        "lng": lng,
    }

    return jsonify(
        {
            "success": True,
            "user": user_payload,
            "data": result.get("data") or result.get("message"),
        }
    ), 200


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_form"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_form"))

    return render_template("dashboard.html", user=session.get("user"))


@app.route("/ai-chat")
def ai_chat():
    if "user" not in session:
        return redirect(url_for("login_form"))

    return render_template("ai_chat.html", user=session.get("user"))


@app.route("/api/admin/users", methods=["GET"])
def admin_list_users():
    _, error_response = require_session_user_json()
    if error_response:
        return error_response

    query_text = request.args.get("query", "")
    limit = request.args.get("limit", default=50, type=int) or 50

    try:
        users = firebase_admin_service.list_users(query_text=query_text, limit=limit)
        return jsonify({"success": True, "data": users})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/api/admin/system-notifications", methods=["POST"])
def admin_send_system_notification():
    current_user, error_response = require_session_user_json()
    if error_response:
        return error_response

    payload = request.get_json(silent=True) or {}
    student_id = (payload.get("studentId") or "").strip()
    title = (payload.get("title") or "").strip()
    body = (payload.get("body") or "").strip()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    if not student_id or not title or not body:
        return jsonify(
            {
                "success": False,
                "error": "Missing studentId, title, or body",
            }
        ), 400

    sender_id = (
        current_user.get("studentId")
        or current_user.get("username")
        or current_user.get("name")
    )

    try:
        result = firebase_admin_service.send_system_notification(
            student_id=student_id,
            title=title,
            body=body,
            sender_id=sender_id,
            payload=data,
        )
        return jsonify({"success": True, "data": result})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/api/send-notification", methods=["POST"])
def api_send_push_notification():
    payload = request.get_json(silent=True) or {}
    receiver_id = payload.get("receiverId")
    title = payload.get("title")
    body = payload.get("body")
    msg_type = payload.get("type", "system")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    if not receiver_id or not title or not body:
        return jsonify({"success": False, "error": "Missing params"}), 400

    try:
        result = firebase_admin_service.send_fcm_push(
            student_id=receiver_id,
            title=title,
            body=body,
            type=msg_type,
            payload=data
        )
        return jsonify({"success": True, "push": result})
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/schedule", methods=["POST"])
def get_schedule_endpoint():
    user = get_session_user()
    req_data = request.get_json(silent=True) or {}
    
    # Ưu tiên lấy studentId từ client, nếu không có thì lấy username của chính Admin
    username = req_data.get("studentId") or req_data.get("username") or (user.get("username") if user else None)
    password = req_data.get("password") or (user.get("password") if user else None)
    domain = req_data.get("domain") or (user.get("domain") if user else None)

    if not username or not password or not domain:
        return jsonify(
            {"success": False, "error": "Missing username, password, or domain"}
        ), 400

    try:
        result = main.run_case(username, password, domain, "schedule")

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 200

        return jsonify(
            {
                "success": True,
                "data": result.get("data") or result.get("message"),
            }
        )
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


@app.route("/student_marks", methods=["POST"])
def get_student_marks_endpoint():
    user = get_session_user()
    req_data = request.get_json(silent=True) or {}
    
    # Ưu tiên lấy studentId từ client, nếu không có thì lấy username của chính Admin
    username = req_data.get("studentId") or req_data.get("username") or (user.get("username") if user else None)
    password = req_data.get("password") or (user.get("password") if user else None)
    domain = req_data.get("domain") or (user.get("domain") if user else None)

    if not username or not password or not domain:
        return jsonify(
            {"success": False, "error": "Missing username, password, or domain"}
        ), 400

    try:
        result = main.run_case(username, password, domain, "get_student_marks")

        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 200

        return jsonify(
            {
                "success": True,
                "data": result.get("data"),
            }
        )
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


APP_ID = "2180e7a7f45c4177af40663a590242d0"
APP_CERTIFICATE = "594818ccd03748a58129514c98f17863"


@app.route("/agora/token", methods=["GET"])
def generate_token():
    channel_name = request.args.get("channel")
    uid = request.args.get("uid")

    if not channel_name or not uid:
        return jsonify({"error": "Missing channel or uid"}), 400

    uid = int(uid)
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + 3600

    token = RtcTokenBuilder.buildTokenWithUid(
        APP_ID,
        APP_CERTIFICATE,
        channel_name,
        uid,
        1,
        privilege_expired_ts,
    )

    return jsonify(
        {
            "token": token,
            "channel": channel_name,
            "uid": uid,
            "expireAt": privilege_expired_ts,
        }
    )


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat_endpoint():
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    req_data = request.get_json()
    message = req_data.get("message")
    subject_name = req_data.get("subjectName", "Không xác định")
    schedule_context = req_data.get("scheduleContext", "Không có thông tin")
    history = req_data.get("history", [])

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    # Cấu hình Ollama
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
    
    # Xây dựng danh sách tin nhắn cho Ollama
    ollama_messages = [
        {
            "role": "system",
            "content": (
                "Bạn là 'Trợ lý Học tập AI' thông minh và tận tâm tích hợp trong ứng dụng Lịch Sinh Viên. "
                "Nhiệm vụ của bạn là hỗ trợ sinh viên quản lý thời gian, tóm tắt kiến thức và giải đáp thắc mắc học tập.\n\n"
                
                "PHONG CÁCH LÀM VIỆC:\n"
                "- Ngôn ngữ: Tiếng Việt, chuyên nghiệp nhưng gần gũi, truyền cảm hứng học tập.\n"
                "- Trình bày: Sử dụng Markdown một cách triệt để. Dùng BẢNG để so sánh, DANH SÁCH để tóm tắt các bước, và IN ĐẬM các từ khóa quan trọng.\n"
                "- Độ dài: Trả lời súc tích, tập trung vào trọng tâm, tránh nói dông dài.\n\n"
                
                "QUY TẮC XỬ LÝ DỮ LIỆU:\n"
                "- NGỮ CẢNH: Bạn được cung cấp 'Môn học hiện tại' và 'Lịch học 3 ngày tới'. Hãy chủ động sử dụng dữ liệu này để đưa ra lời khuyên. "
                "Ví dụ: Nếu thấy ngày mai có bài kiểm tra, hãy nhắc nhở người dùng ôn tập ngay.\n"
                "- TRUNG THỰC: Chỉ trả lời dựa trên dữ liệu thật. Tuyệt đối không bịa đặt điểm số, deadline hay lịch học nếu không có trong ngữ cảnh.\n"
                "- PHẠM VI: Bạn có thể tán gẫu nhẹ nhàng, hài hước hoặc hỗ trợ tìm kiếm kiến thức tổng quát nếu người dùng yêu cầu. Tuy nhiên, sau mỗi câu trả lời ngoài lề, hãy luôn tìm cách nhắc nhở khéo léo về lịch học hoặc gợi ý một chủ đề ôn tập liên quan đến môn học của họ.\n\n"
                
                "KHI NGƯỜI DÙNG HỎI BÀI:\n"
                "1. Giải thích khái niệm một cách dễ hiểu nhất.\n"
                "2. Đưa ra ví dụ minh họa thực tế.\n"
                "3. Gợi ý 3 câu hỏi ôn tập để người dùng tự kiểm tra kiến thức.\n\n"
                
                "KHI NGƯỜI DÙNG TÁN GẪU/HỎI NGOÀI LỀ:\n"
                "- Hãy trả lời một cách thông minh, hóm hỉnh.\n"
                "- Sau đó chốt lại bằng một câu đại loại như: 'Giải trí thế đủ rồi, bạn có muốn mình cùng xem lại lịch học ngày mai không?' hoặc 'Kiến thức này thú vị đấy, nhưng đừng quên hôm nay bạn có môn X cần chuẩn bị nhé!'"
            )
        }
    ]

    # Thêm lịch sử chat (nếu có)
    for h in history:
        ollama_messages.append({
            "role": h.get("role"),
            "content": h.get("content")
        })

    # Thêm câu hỏi hiện tại với ngữ cảnh
    user_content = f"Ngữ cảnh môn học: {subject_name}\nNgữ cảnh lịch học/deadline: {schedule_context}\nCâu hỏi: {message}"
    ollama_messages.append({
        "role": "user",
        "content": user_content
    })

    try:
        import requests
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:3b",
                "messages": ollama_messages,
                "stream": False
            },
            timeout=60 # Tăng timeout vì AI có thể trả lời lâu
        )
        
        if response.status_code != 200:
            return jsonify({
                "success": False, 
                "error": "Trợ lý học tập hiện chưa sẵn sàng. Vui lòng thử lại sau.",
                "details": response.text
            }), 503

        ai_response = response.json()
        reply = ai_response.get("message", {}).get("content", "").strip()

        if not reply:
            return jsonify({
                "success": False, 
                "error": "Mình chưa tạo được câu trả lời, bạn thử hỏi lại rõ hơn nhé."
            }), 200

        return jsonify({
            "success": True,
            "reply": reply
        })

    except Exception as e:
        print(f"[AI ERROR] {str(e)}")
        return jsonify({
            "success": False, 
            "error": "Trợ lý học tập hiện chưa sẵn sàng. Vui lòng thử lại sau."
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
