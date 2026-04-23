import requests, re
from bs4 import BeautifulSoup
import hashlib

BASE_URL = "http://220.231.119.171/kcntt"

from urllib.parse import urlparse, urlunparse


def get_base_with_session(url: str) -> str:
    parsed = urlparse(url)

    # Tách path thành các phần
    parts = parsed.path.strip("/").split("/")

    # Nếu có ít nhất 2 segment thì bỏ 2 cái cuối
    if len(parts) >= 2:
        parts = parts[:-2]
    elif parts:
        parts = parts[:-1]

    # Ghép lại path
    new_path = "/" + "/".join(parts) if parts else ""

    # Ghép URL base lại
    return urlunparse((parsed.scheme, parsed.netloc, new_path, "", "", ""))
def login(username, password):
    try:
        session = requests.Session()
        login_url = f"{BASE_URL}/Login.aspx?url={BASE_URL}/Home.aspx"

        resp = session.get(login_url, verify=False, timeout=15)
        login_url_with_session = resp.url
        soup = BeautifulSoup(resp.text, "html.parser")

        viewstate_el = soup.find("input", {"id": "__VIEWSTATE"})
        viewstategen_el = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})
        eventvalidation_el = soup.find("input", {"id": "__EVENTVALIDATION"})

        if not viewstate_el or not viewstategen_el or not eventvalidation_el:
            return {
                "error": True,
                "errorCode": "ICTU_PARSE_ERROR",
                "message": "Không đọc được form đăng nhập ICTU"
            }

        viewstate = viewstate_el.get("value")
        viewstategen = viewstategen_el.get("value")
        eventvalidation = eventvalidation_el.get("value")

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        md5_pass = hashlib.md5(password.encode()).hexdigest()

        login_data = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__EVENTVALIDATION": eventvalidation,
            "PageHeader1$drpNgonNgu": "010527EFBEB84BCA8919321CFD5C3A34",
            "PageHeader1$hidisNotify": "0",
            "PageHeader1$hidValueNotify": ".",
            "txtUserName": username,
            "txtPassword": md5_pass,
            "btnSubmit": "Đăng nhập",
            "hidUserId": "",
            "hidUserFullName": "",
            "hidTrainingSystemId": ""
        }

        login_headers = headers.copy()
        login_headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://220.231.119.171",
            "Referer": login_url
        })

        response = session.post(
            login_url_with_session,
            headers=login_headers,
            data=login_data,
            verify=False,
            timeout=15
        )

        if "Login.aspx" in response.url:
            return {
                "error": True,
                "errorCode": "INVALID_CREDENTIAL",
                "message": "Sai tài khoản hoặc mật khẩu"
            }

        base_with_session = get_base_with_session(response.url)
        if not base_with_session:
            return {
                "error": True,
                "errorCode": "ICTU_BASE_URL_ERROR",
                "message": "Không xác định được đường dẫn phiên đăng nhập"
            }

        base_with_session = get_base_with_session(response.url)
        if not base_with_session:
            return {
                "error": True,
                "errorCode": "ICTU_BASE_URL_ERROR",
                "message": "Không xác định được đường dẫn phiên đăng nhập"
            }

        return {
            "error": False,
            "session": session,
            "base": base_with_session
        }

    except requests.Timeout:
        return {
            "error": True,
            "errorCode": "ICTU_TIMEOUT",
            "message": "Kết nối tới ICTU bị timeout"
        }
    except Exception as e:
        return {
            "error": True,
            "errorCode": "ICTU_UNKNOWN_ERROR",
            "message": str(e)
        }