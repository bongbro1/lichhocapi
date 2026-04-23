import requests
import json
import base64
import time
from urllib.parse import unquote

def login(username, password):
    """
    Đăng nhập TNUT sử dụng REST API (đã tối ưu).
    Lấy đầy đủ thông tin profile sinh viên.
    """
    t_start = time.time()
    try:
        session = requests.Session()
        
        # 1. Đăng nhập qua pn-signin
        login_info = {
            "username": username,
            "password": password,
            "uri": "https://portal.tnut.edu.vn/#/home"
        }
        login_info_str = json.dumps(login_info)
        code_base64 = base64.b64encode(login_info_str.encode()).decode()
        
        login_url = f"https://portal.tnut.edu.vn/api/pn-signin?code={code_base64}&gopage=&mgr=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        
        t1 = time.time()
        response = session.get(login_url, headers=headers, allow_redirects=False, timeout=10)
        t_login = time.time() - t1
        
        redirect_url = response.headers.get("Location")
        if not redirect_url or "CurrUser=" not in redirect_url:
            return {"error": True, "errorCode": "INVALID_CREDENTIAL", "message": "Sai tài khoản hoặc mật khẩu (TNUT)"}
            
        curr_user_base64 = unquote(redirect_url.split("CurrUser=")[1])
        try:
            curr_user_data = json.loads(base64.b64decode(curr_user_base64).decode())
        except Exception:
            missing_padding = len(curr_user_base64) % 4
            if missing_padding: curr_user_base64 += '=' * (4 - missing_padding)
            curr_user_data = json.loads(base64.b64decode(curr_user_base64).decode())

        if not curr_user_data.get("result"):
            return {"error": True, "message": "Portal TNUT từ chối đăng nhập"}
            
        token = curr_user_data.get("access_token")
        
        # 2. Lấy thông tin chi tiết sinh viên (Profile)
        api_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": headers["User-Agent"],
            "ua": "KDU3w7d9w5nDksKIw7BtRDE1w79zw5nDncKHwpQMOyxTw6sGwqPCqcO7wpQaP0ZJwpUDwqLCosOpwo4b"
        }
        
        t2 = time.time()
        # Lấy Ngành, Lớp
        info_url = "https://portal.tnut.edu.vn/api/dkmh/w-locsinhvieninfo"
        info_resp = session.post(info_url, headers=api_headers, json={}, timeout=5)
        
        major = ""
        class_name = ""
        school_name = "Trường Đại học Kỹ thuật Công nghiệp - ĐHTN"
        
        if info_resp.status_code == 200:
            info_data = info_resp.json().get("data", {})
            major = info_data.get("nganh", "")
            class_name = info_data.get("lop", "")
            school_name = info_data.get("ten_truong", school_name)
            
        # 3. Lấy Học kỳ cuối (nhhk_cuoi)
        term_url = "https://portal.tnut.edu.vn/api/sch/w-locdshockytkbuser"
        term_payload = {"filter": {"is_tieng_anh": None}, "additional": {"paging": {"limit": 1, "page": 1}, "ordering": [{"name": "hoc_ky", "order_type": 1}]}}
        term_resp = session.post(term_url, headers=api_headers, json=term_payload, timeout=5)
        
        nhhk_cuoi = curr_user_data.get("nhhk_cuoi") or ""
        if term_resp.status_code == 200:
            term_data = term_resp.json().get("data", {})
            # Thường học kỳ mới nhất nằm ở đầu danh sách do ordering hoc_ky desc (order_type 1)
            ds_hk = term_data.get("ds_hoc_ky", [])
            if ds_hk:
                nhhk_cuoi = ds_hk[0].get("hoc_ky", nhhk_cuoi)
        
        t_info = time.time() - t2

        # 4. Tổng hợp user_data
        user_data = {
            "studentId": curr_user_data.get("userName") or curr_user_data.get("id"),
            "name": curr_user_data.get("FullName") or curr_user_data.get("name"),
            "token": token,
            "major": major,
            "class_name": class_name,
            "school_name": school_name,
            "nhhk_cuoi": nhhk_cuoi,
            "cookie": "; ".join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
        }
        
        t_total = time.time() - t_start
        print(f"✅ TNUT Login: {user_data['name']} ({t_total:.2f}s) [Login: {t_login:.2f}s, Info: {t_info:.2f}s]", flush=True)
        return user_data

    except Exception as e:
        print(f"❌ TNUT Login Error: {str(e)}", flush=True)
        return {"error": True, "message": f"Lỗi kết nối TNUT: {str(e)}"}