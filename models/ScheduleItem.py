from typing import Optional
from datetime import datetime

class ScheduleItem:
    def __init__(
        self,
        id: str,               # UUID hoặc STT (dạng string)
        title: str,            # Tên môn học / hoạt động
        code: Optional[str] = None,   # Mã học phần (nếu có)
        credit: Optional[int] = None, # Số tín chỉ (nếu có)
        teacher: Optional[str] = None,# Giảng viên (nếu có)
        location: Optional[str] = None,# Phòng học / link meet
        date: Optional[datetime] = None,   # Ngày thi / ngày học
        startHour: Optional[str] = None,
        endHour: Optional[str] = None,
        startPeriod: Optional[str] = None, # tiết học bắt đầu
        endPeriod: Optional[str] = None,   # tiết học kết thúc
        examType: Optional[str] = None,    # Hình thức thi (nếu là lịch thi)
        examSession: Optional[str] = None, # Ca thi (nếu là lịch thi)
        studentId: Optional[str] = None,   # Số báo danh (nếu là lịch thi)
        note: Optional[str] = None,         # Ghi chú
        isExam: Optional[bool] = False
    ):
        self.id = id
        self.title = title
        self.code = code
        self.credit = credit
        self.teacher = teacher
        self.location = location
        self.date = date
        self.startHour = startHour
        self.endHour = endHour
        self.startPeriod = startPeriod
        self.endPeriod = endPeriod
        self.examType = examType
        self.examSession = examSession
        self.studentId = studentId
        self.note = note
        self.isExam = isExam

    def to_dict(self):
        data = self.__dict__.copy()
        if isinstance(self.date, datetime):
            # format ISO cho an toàn
            data["date"] = self.date.strftime("%Y-%m-%d")
        return data
