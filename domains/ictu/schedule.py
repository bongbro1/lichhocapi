import json
import re
import os
import uuid
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from typing import Tuple, Optional
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from models.ScheduleItem import ScheduleItem

# Bảng thời gian các tiết trong ngày
PERIODS = [
    (6, 45), (7, 35), (8, 25), (9, 15), (10, 5),   # Sáng
    (13, 0), (13, 50), (14, 40), (15, 30), (16, 20), # Chiều
    (18, 15), (19, 5), (19, 55), (20, 45), (21, 35)  # Tối
]

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%d/%m/%Y")

def compute_time_range(start_period: int, end_period: int) -> Tuple[str, str]:
    hour, minute = PERIODS[start_period]
    time_start = f"{hour:02d}:{minute:02d}"

    current_hour, current_minute = hour, minute
    for p in range(start_period, end_period + 1):
        current_minute += 50
        if p % 5 == 1: current_minute += 10
        else: current_minute += 5
        current_hour += current_minute // 60
        current_minute = current_minute % 60

    time_end = f"{current_hour:02d}:{current_minute:02d}"
    return time_start, time_end

def parse_text_to_time(cell_text: str, is_exam: bool) -> Tuple[Optional[str], Optional[str]]:
    if is_exam:
        match = re.search(r'\((\d{1,2}:\d{2})-(\d{1,2}:\d{2})\)', cell_text)
        return (match.group(1), match.group(2)) if match else (None, None)
    else:
        try:
            parts = re.findall(r'\d+', cell_text)
            if len(parts) >= 2:
                return compute_time_range(int(parts[0]) - 1, int(parts[1]) - 1)
        except: pass
    return None, None

def get_schedule(session, base_with_session):
    url = f"{base_with_session}/Reports/Form/StudentTimeTable.aspx"
    try:
        resp = session.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        data = {h.get("name"): h.get("value", "") for h in soup.find_all("input", type="hidden") if h.get("name")}
        
        today = datetime.today()
        monday = today - timedelta(days=today.weekday())
        data["txtTuNgay"] = (monday - timedelta(days=7)).strftime("%d/%m/%Y")
        data["txtDenNgay"] = (today + timedelta(days=45)).strftime("%d/%m/%Y")
        data["btnView"] = "Xuất file Excel"

        resp_export = session.post(url, data=data, timeout=20)
        if "html" in resp_export.headers.get("Content-Type", "").lower(): return []

        # Parse file Excel dùng openpyxl trực tiếp cho nhanh
        df = pd.read_excel(BytesIO(resp_export.content), header=None, engine="openpyxl")
        
        lessons = []
        week_col, week_start = None, None
        for col_idx in range(df.shape[1]):
            for i in range(min(15, len(df))):
                if "Tuần" in str(df.iat[i, col_idx]):
                    week_col = col_idx; break
            if week_col is not None: break

        if week_col is None: return []

        for _, row in df.iterrows():
            val = str(row[week_col])
            if val.startswith("Tuần"):
                match = re.search(r"\((\d{2}/\d{2}/\d{4})", val)
                if match: week_start = datetime.strptime(match.group(1), "%d/%m/%Y")
                continue
            
            if pd.isna(row[0]) or not str(row[0]).isdigit(): continue

            tiet = str(row[4])
            start_h, end_h = parse_text_to_time(tiet, False)
            thu = int(float(row[3])) if pd.notna(row[3]) else None
            
            if thu and week_start:
                ngay_hoc = week_start + timedelta(days=thu - 2)
                lessons.append(ScheduleItem(
                    id=str(uuid.uuid4()), title=str(row[1]).strip(), code="", credit=0,
                    startHour=start_h, endHour=end_h, teacher=str(row[2]).split("\n")[0].strip(),
                    location=str(row[5]).strip(), startPeriod=tiet.split(" --> ")[0].strip(),
                    endPeriod=tiet.split(" --> ")[1].strip(), date=ngay_hoc,
                    studentId=data.get("txtMaSV", "unknown"), isExam=False
                ))
        return lessons
    except: return []

def get_exam_list(session, base_with_session):
    url = f"{base_with_session}/StudentViewExamList.aspx"
    try:
        resp = session.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "tblCourseList"})
        exams = []
        if table:
            for row in table.find_all("tr")[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 10 and cols[0].isdigit():
                    s_h, e_h = parse_text_to_time(cols[5], True)
                    exams.append(ScheduleItem(
                        id=str(uuid.uuid4()), title=cols[2], code=cols[1],
                        credit=int(cols[3]) if cols[3].isdigit() else 0,
                        date=parse_date(cols[4]), startHour=s_h, endHour=e_h,
                        examSession=cols[5], examType=cols[6], studentId=cols[7],
                        location=cols[8], note=cols[9] if len(cols) > 9 else None, isExam=True
                    ))
        return exams
    except: return []

def get_student_info(session, base_with_session):
    try:
        url = f"{base_with_session}/StudentMark.aspx"
        resp = session.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            "studentId": soup.find("span", id="lblStudentCode").text.strip(),
            "name": soup.find("span", id="lblStudentName").text.strip(),
            "major": soup.find("input", id="hidFieldName")["value"].strip(),
            "class_name": soup.find("span", id="lblAdminClass").text.strip(),
            "school_name": "Trường đại học Công nghệ thông tin và Truyền thông Thái Nguyên"
        }
    except: return {"studentId": "", "name": "", "major": "", "class_name": "", "school_name": ""}

def get_full_schedule(session, base_with_session):
    # Chạy song song với 5 workers để ép tốc độ
    with ThreadPoolExecutor(max_workers=5) as executor:
        f_exams = executor.submit(get_exam_list, session, base_with_session)
        f_lessons = executor.submit(get_schedule, session, base_with_session)
        f_user = executor.submit(get_student_info, session, base_with_session)

        exams = f_exams.result()
        lessons = f_lessons.result()
        user_info = f_user.result()
    
    all_lessons = exams + lessons
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    with open(os.path.join(data_dir, f"{user_info['studentId']}_schedule.json"), "w", encoding="utf-8") as f:
        json.dump({**user_info, "lessons": [l.to_dict() for l in all_lessons]}, f, ensure_ascii=False, indent=2)
    
    return all_lessons, user_info
