import os
import json
import requests

import uuid
from datetime import datetime

def find_ds_tuan_tkb(obj):
    """Đệ quy tìm key 'ds_tuan_tkb' trong dict hoặc list"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "ds_tuan_tkb" and isinstance(v, list):
                return v
            else:
                found = find_ds_tuan_tkb(v)
                if found is not None:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_ds_tuan_tkb(item)
            if found is not None:
                return found
    return None

def build_period_map(ds_tiet_trong_ngay):
    """Xây map tiết -> (giờ bắt đầu, giờ kết thúc)"""
    return {t.get("tiet"): (t.get("gio_bat_dau"), t.get("gio_ket_thuc")) for t in ds_tiet_trong_ngay}

def parse_tnut_schedule(user_data, data):
    ds_tuan_tkb = find_ds_tuan_tkb(data)
    if not ds_tuan_tkb:
        return []

    # Lấy danh sách tiết trong ngày từ data (nếu có)
    ds_tiet_trong_ngay = data.get("ds_tiet_trong_ngay", [])
    period_map = build_period_map(ds_tiet_trong_ngay)

    lessons = []
    student_id = user_data.get("studentId") or user_data.get("ma_sv")
    for week in ds_tuan_tkb:
        for tkb in week.get("ds_thoi_khoa_bieu", []):
            ngay_hoc = tkb.get("ngay_hoc")
            try:
                date_str = datetime.strptime(ngay_hoc[:10], "%Y-%m-%d").strftime("%Y-%m-%d") if ngay_hoc else None
            except:
                date_str = None

            start_period = tkb.get("tiet_bat_dau")
            end_period = start_period + tkb.get("so_tiet", 0) - 1 if start_period else None

            # Lấy giờ bắt đầu và kết thúc từ period_map
            start_hour, _ = period_map.get(start_period, (None, None))
            _, end_hour = period_map.get(end_period, (None, None))

            lessons.append({
                "id": str(uuid.uuid4()),
                "title": tkb.get("ten_mon", ""),
                "code": tkb.get("ma_mon", ""),
                "credit": int(tkb.get("so_tin_chi") or 0),
                "teacher": tkb.get("ten_giang_vien", ""),
                "location": tkb.get("ma_phong", ""),
                "date": date_str,
                "startHour": start_hour,
                "endHour": end_hour,
                "startPeriod": str(start_period) if start_period else None,
                "endPeriod": str(end_period) if end_period else None,
                "examType": None,
                "examSession": None,
                "studentId": student_id,
                "note": None,
                "isExam": False
            })
    return lessons

def get_current_term(user_data):
    """
    Lấy học kỳ hiện tại theo ngày từ endpoint w-locdshockytkbuser
    """
    url = "https://portal.tnut.edu.vn/api/sch/w-locdshockytkbuser"
    token = user_data.get("token")
    cookies = user_data.get("cookie")

    if not token:
        raise ValueError("user_data phải có trường 'token'")

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://portal.tnut.edu.vn",
        "referer": "https://portal.tnut.edu.vn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "cookie": cookies
    }

    payload = {
        "filter": {"is_tieng_anh": None},
        "additional": {
            "paging": {"limit": 100, "page": 1},
            "ordering": [{"name": "hoc_ky", "order_type": 1}]
        }
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", {})

    return data.get("hoc_ky_theo_ngay_hien_tai")

def get_full_schedule(user_data):
    
    """
    Lấy thời khóa biểu TNUT async và lưu vào file JSON.

    user_data: dict, cần có 'token', 'ma_sv', 'ten_day_du', 'nganh', 'nhhk_cuoi'
    """
    url = "https://portal.tnut.edu.vn/api/sch/w-locdstkbtuanusertheohocky"

    token = user_data.get("token")
    
    cookies = user_data.get("cookie")
    current_term = get_current_term(user_data)
    if not token:
        raise ValueError("user_data phải có trường 'token'")

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://portal.tnut.edu.vn",
        "referer": "https://portal.tnut.edu.vn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "cookie": cookies
    }

    payload = {
        "filter": {
            "hoc_ky": current_term,
            "ten_hoc_ky": ""
        },
        "additional": {
            "paging": {"limit": 100, "page": 1},
            "ordering": [{"name": None, "order_type": None}]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "data" not in data:
            print("Lỗi: response không có key 'data'", flush=True)
            return {"error": "Response không có key 'data'"}
    except Exception as e:
        print("Lỗi khi request thời khóa biểu:", e, flush=True)
        return None

    # Lưu theo cấu trúc data_dir
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, f"{user_data['studentId']}_schedule.json")

    all_lessons = parse_tnut_schedule(user_data, data.get("data", {}))

    user_info = get_student_info(user_data)

    # Ghi file JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            **user_info,
            "lessons": all_lessons
        }, f, ensure_ascii=False, indent=2)

    # Trả về tuple
    return all_lessons, user_info

def get_student_info(user_data):
    user_info = {
        "studentId": user_data["studentId"],
        "name": user_data["name"],
        "major": user_data.get("major"),
        "class_name": user_data.get("class_name"),
        "school_name": user_data.get("school_name")
    }
    return user_info