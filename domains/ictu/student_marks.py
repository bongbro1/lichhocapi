import uuid
from bs4 import BeautifulSoup
from datetime import datetime

def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def parse_date(text, fmt="%d/%m/%Y"):
    try:
        return datetime.strptime(text, fmt).date()
    except:
        return None

def get_student_marks(session, base_with_session):
    url = f"{base_with_session}/StudentMark.aspx"
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Lấy tên + mã sinh viên
    studentInfo = {
        "name": soup.find(id="lblStudentName").text.strip(),
        "studentId": soup.find(id="lblStudentCode").text.strip(),
    }

    # Tìm dòng "Toàn khóa"
    table = soup.find("table", id="grdResult")
    if table:
        rows = table.find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if cols and cols[0] == "Toàn khóa":
                studentInfo.update({
                    "totalCredits": int(cols[6]) if cols[6].isdigit() else 0,
                    "stcTL": int(cols[6]) if cols[6].isdigit() else 0,
                    "tbcHS10": safe_float(cols[8]),
                    "tbcHS4": safe_float(cols[10]),
                    "dtbTLHS10": safe_float(cols[2]),
                    "dtbTLHS4": safe_float(cols[4]),
                })
                break
    

    # Lấy danh sách môn học
    subject_table = soup.find("table", id="tblStudentMark")
    subjects = []

    if subject_table:
        rows = subject_table.find_all("tr")  # lưu ý phải là subject_table, không phải table
        for row in rows:
            # Lọc bỏ header
            if 'DataGridFixedHeader' in row.get('class', []):
                continue
            
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 14:
                subjects.append({
                    "name": cols[2],
                    "code": cols[1],
                    "credits": int(cols[3]) if cols[3].isdigit() else 0,
                    "cc": safe_float(cols[10]),
                    "thi": safe_float(cols[11]),
                    "tkhp": safe_float(cols[12]),
                    "letter": cols[13],
                    "rank": cols[8]
                })

    result = {
        "studentInfo": studentInfo,
        "subjects": subjects
    }

    return result