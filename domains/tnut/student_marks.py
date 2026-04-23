import os
import json
import requests

def get_student_info_from_marks_json(user_data, data):
    ds_hk = data.get("ds_diem_hocky", [])

    totalCredits = 0
    stcTL = 0
    dtbTLHS10 = 0.0
    dtbTLHS4 = 0.0
    tbcHS10 = 0.0
    tbcHS4 = 0.0
    latestHK = None

    # Cập nhật tích lũy từ tất cả học kỳ

    # Duyệt ngược để tìm học kỳ gần nhất có điểm tổng kết
    for hk in ds_hk:
        so_tin_chi_dat_tich_luy = hk.get("so_tin_chi_dat_tich_luy")
        if so_tin_chi_dat_tich_luy not in (None, "", 0):
            tbcHS10 = float(0)
            tbcHS4 = float(0)
            dtbTLHS4 = float(hk["dtb_tich_luy_he_4"])
            dtbTLHS10 = float(hk["dtb_tich_luy_he_10"])
            totalCredits = int(hk["so_tin_chi_dat_tich_luy"])
            break

    return {
        "name": user_data.get("name"),
        "studentId": user_data.get("studentId"),
        "totalCredits": totalCredits,
        "stcTL": totalCredits,
        "tbcHS10": tbcHS10,
        "tbcHS4": tbcHS4,
        "dtbTLHS10": dtbTLHS10,
        "dtbTLHS4": dtbTLHS4
    }


def parse_student_marks(data):
    subjects = []

    ds_hk = data.get("ds_diem_hocky", [])
    for hk in ds_hk:
        ds_mon = hk.get("ds_diem_mon_hoc", [])
        for mon in ds_mon:
            # Bỏ qua các dict rỗng
            if not mon:
                continue
            # Bỏ qua môn không tính điểm TB tích lũy
            if mon.get("ly_do_khong_tinh_diem_tbtl"):
                continue

            subject = {
                "name": mon.get("ten_mon", "").strip() or "unknown",
                "code": mon.get("ma_mon", "").strip() or "unknown",
                "credits": int(mon.get("so_tin_chi") or 0),
                "cc": float(mon.get("diem_giua_ky") or 0.0),
                "thi": float(mon.get("diem_thi") or 0.0),
                "tkhp": float(mon.get("diem_tk") or 0.0),
                "letter": mon.get("diem_tk_chu") or "",
                "rank": mon.get("ket_qua")
            }

            # Nếu muốn rank dạng chữ
            ket_qua_map = {1: "DAT", 0: "CHUA DAT"}
            subject["rank"] = ket_qua_map.get(mon.get("ket_qua", -1), "")

            subjects.append(subject)

    return subjects

def get_student_marks(user_data):
    url = "https://portal.tnut.edu.vn/api/srm/w-locdsdiemsinhvien?hien_thi_mon_theo_hkdk=false"

    token = user_data.get("token")
    cookies = user_data.get("cookie", "")
    
    if not token:
        raise ValueError("user_data phải có trường 'token'")

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "authorization": f"Bearer {token}",
        "idpc": "0",
        "origin": "https://portal.tnut.edu.vn",
        "priority": "u=1, i",
        "referer": "https://portal.tnut.edu.vn/",
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "ua": "KDU3w7d9w5nDksKIw7BtRDE1w79zw5nDncKHwpQMOyxTw6sGwqPCqcO7wpQaP0ZJwpUDwqLCosOpwo4b",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "cookie": cookies
    }

    try:
        response = requests.post(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        if "data" not in data:
            print("Lỗi: response không có key 'data'", flush=True)
            return {"error": "Response không có key 'data'"}
    except Exception as e:
        print("Lỗi khi request điểm sinh viên:", e, flush=True)
        return {"error": str(e)}

    student_info = get_student_info_from_marks_json(user_data,data.get("data", {}))
    subjects = parse_student_marks(data.get("data", {}))
    # Lưu theo cấu trúc data_dir
    result = {
        "studentInfo": student_info,
        "subjects": subjects
    }

    return result