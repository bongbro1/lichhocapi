
from typing import Optional
from flask import request

def normalize_avatar(avatar: Optional[str]) -> Optional[str]:
    """
    Chuẩn hóa URL avatar, lấy host_url trực tiếp từ request.

    :param avatar: chuỗi avatar từ partner.avatar
    :return: URL đầy đủ hoặc None nếu không có avatar
    """
    if not avatar:
        return None
    if avatar.startswith("http"):
        return avatar
    # request.host_url đã có '/' cuối, chỉ cần lstrip('/') avatar
    return f"{request.host_url}{avatar.lstrip('/')}"
