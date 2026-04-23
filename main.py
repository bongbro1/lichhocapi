import time

import domains.ictu as ictu
import domains.tnut as tnut
import sys, os, datetime
import asyncio

from database.fake_db import remove_user, validate_user
sys.path.append(os.path.dirname(__file__))
import time
import threading

SESSION_TTL = 15 * 60
session_store = {}
session_lock = threading.Lock()

def make_key(username, domain):
    return f"{domain}:{username}"

def get_cached_session(username, domain):
    key = make_key(username, domain)
    with session_lock:
        item = session_store.get(key)
        if not item:
            return None

        if time.time() - item["last_used"] > SESSION_TTL:
            session_store.pop(key, None)
            return None

        item["last_used"] = time.time()
        return item

def save_cached_session(username, domain, session, base):
    key = make_key(username, domain)
    with session_lock:
        session_store[key] = {
            "session": session,
            "base": base,
            "last_used": time.time()
        }

def clear_cached_session(username, domain):
    key = make_key(username, domain)
    with session_lock:
        session_store.pop(key, None)

def get_or_login_ictu(username, password):
    cached = get_cached_session(username, "ICTU")
    if cached:
        return {
            "error": False,
            "session": cached["session"],
            "base": cached["base"]
        }

    result = ictu.login(username, password)
    if result.get("error"):
        return result

    session = result["session"]
    base = result["base"]

    save_cached_session(username, "ICTU", session, base)

    return {
        "error": False,
        "session": session,
        "base": base
    }

def run_case(username, password, domain, action_type):
    t0 = time.time()

    valid = validate_user(username, password, domain)
    t1 = time.time()
    print(f"[TIME] validate_user: {t1 - t0:.2f}s", flush=True)

    if not valid:
        print(f"[TIME] TOTAL failed_validate: {time.time() - t0:.2f}s", flush=True)
        return {"error": "Thông tin tài khoản không hợp lệ"}

    if domain == "ICTU":
        try:
            login_result = get_or_login_ictu(username, password)

            if login_result.get("error"):
                return login_result

            session = login_result["session"]
            base = login_result["base"]
            t2 = time.time()
            print(f"[TIME] get_or_login_ictu: {t2 - t1:.2f}s", flush=True)

            if not session:
                remove_user(username)
                print(f"[TIME] TOTAL login_failed: {time.time() - t0:.2f}s", flush=True)
                return {"error": "Đăng nhập ICTU thất bại"}

            if action_type == 'login':
                data = ictu.get_student_info(session, base)
                t3 = time.time()
                print(f"[TIME] get_student_info: {t3 - t2:.2f}s", flush=True)
                print(f"[TIME] TOTAL login: {t3 - t0:.2f}s", flush=True)

                data.update({
                    'username': username,
                    'password': password,
                    'domain': domain
                })
                return {'success': True, 'data': serialize(data)}

            elif action_type == 'schedule':
                try:
                    data, user_info = ictu.get_full_schedule(session, base)
                    t3 = time.time()
                    print(f"[TIME] get_full_schedule: {t3 - t2:.2f}s", flush=True)
                    print(f"[TIME] TOTAL schedule: {t3 - t0:.2f}s", flush=True)

                    return {
                        "success": True,
                        "data": serialize(data),
                        "user": user_info
                    }

                except Exception as e:
                    t_err = time.time()
                    print(f"[TIME] get_full_schedule failed after: {t_err - t2:.2f}s", flush=True)
                    print(f"[ERROR] schedule failed, relogin: {str(e)}", flush=True)

                    clear_cached_session(username, domain)
                    t4 = time.time()
                    print(f"[TIME] clear_cached_session: {t4 - t_err:.2f}s", flush=True)

                    session, base = ictu.login(username, password)
                    t5 = time.time()
                    print(f"[TIME] relogin ictu.login: {t5 - t4:.2f}s", flush=True)

                    if not session:
                        print(f"[TIME] TOTAL schedule_relogin_failed: {time.time() - t0:.2f}s", flush=True)
                        return {"error": "Session hết hạn và đăng nhập lại thất bại"}

                    save_cached_session(username, domain, session, base)
                    t6 = time.time()
                    print(f"[TIME] save_cached_session: {t6 - t5:.2f}s", flush=True)

                    data, user_info = ictu.get_full_schedule(session, base)
                    t7 = time.time()
                    print(f"[TIME] retry get_full_schedule: {t7 - t6:.2f}s", flush=True)
                    print(f"[TIME] TOTAL schedule_with_retry: {t7 - t0:.2f}s", flush=True)

                    return {
                        "success": True,
                        "data": serialize(data),
                        "user": user_info
                    }

            elif action_type == 'get_student_marks':
                try:
                    data = ictu.get_student_marks(session, base)
                    t3 = time.time()
                    print(f"[TIME] get_student_marks: {t3 - t2:.2f}s", flush=True)
                    print(f"[TIME] TOTAL marks: {t3 - t0:.2f}s", flush=True)

                    return {'success': True, 'data': serialize(data)}

                except Exception as e:
                    t_err = time.time()
                    print(f"[TIME] get_student_marks failed after: {t_err - t2:.2f}s", flush=True)
                    print(f"[ERROR] marks failed, relogin: {str(e)}", flush=True)

                    clear_cached_session(username, domain)
                    t4 = time.time()
                    print(f"[TIME] clear_cached_session: {t4 - t_err:.2f}s", flush=True)

                    session, base = ictu.login(username, password)
                    t5 = time.time()
                    print(f"[TIME] relogin ictu.login: {t5 - t4:.2f}s", flush=True)

                    if not session:
                        print(f"[TIME] TOTAL marks_relogin_failed: {time.time() - t0:.2f}s", flush=True)
                        return {"error": "Session hết hạn và đăng nhập lại thất bại"}

                    save_cached_session(username, domain, session, base)
                    t6 = time.time()
                    print(f"[TIME] save_cached_session: {t6 - t5:.2f}s", flush=True)

                    data = ictu.get_student_marks(session, base)
                    t7 = time.time()
                    print(f"[TIME] retry get_student_marks: {t7 - t6:.2f}s", flush=True)
                    print(f"[TIME] TOTAL marks_with_retry: {t7 - t0:.2f}s", flush=True)

                    return {'success': True, 'data': serialize(data)}

            else:
                print(f"[TIME] TOTAL invalid_action: {time.time() - t0:.2f}s", flush=True)
                return {"error": "action_type không hợp lệ"}

        except Exception as e:
            print(f"[ERROR] run_case ICTU exception: {str(e)}", flush=True)
            print(f"[TIME] TOTAL ictu_exception: {time.time() - t0:.2f}s", flush=True)
            return {"error": str(e)}

    elif domain == "TNUT":
        try:
            t1 = time.time()
            user_data = tnut.login(username, password)
            t2 = time.time()
            print(f"[TIME] tnut.login: {t2 - t1:.2f}s", flush=True)

            if not user_data:
                remove_user(username)
                print(f"[TIME] TOTAL tnut_login_failed: {time.time() - t0:.2f}s", flush=True)
                return {"error": "Đăng nhập TNUT thất bại"}

            if action_type == 'login':
                data = tnut.get_student_info(user_data)
                t3 = time.time()
                print(f"[TIME] tnut.get_student_info: {t3 - t2:.2f}s", flush=True)
                print(f"[TIME] TOTAL tnut_login: {t3 - t0:.2f}s", flush=True)

                data.update({
                    'username': username,
                    'password': password,
                    'domain': domain
                })
                return {'success': True, 'data': serialize(data)}

            elif action_type == 'schedule':
                data, user_info = tnut.get_full_schedule(user_data)
                t3 = time.time()
                print(f"[TIME] tnut.get_full_schedule: {t3 - t2:.2f}s", flush=True)
                print(f"[TIME] TOTAL tnut_schedule: {t3 - t0:.2f}s", flush=True)

                return {"success": True, "data": serialize(data), "user": user_info}

            elif action_type == 'get_student_marks':
                data = tnut.get_student_marks(user_data)
                t3 = time.time()
                print(f"[TIME] tnut.get_student_marks: {t3 - t2:.2f}s", flush=True)
                print(f"[TIME] TOTAL tnut_marks: {t3 - t0:.2f}s", flush=True)

                return {'success': True, 'data': serialize(data)}

            else:
                print(f"[TIME] TOTAL invalid_action: {time.time() - t0:.2f}s", flush=True)
                return {"error": "action_type không hợp lệ"}

        except Exception as e:
            print(f"[ERROR] run_case TNUT exception: {str(e)}", flush=True)
            print(f"[TIME] TOTAL tnut_exception: {time.time() - t0:.2f}s", flush=True)
            return {"error": str(e)}

    else:
        print(f"[TIME] TOTAL invalid_domain: {time.time() - t0:.2f}s", flush=True)
        return {"error": "Miền không hợp lệ"}
    

def serialize(obj):
    if isinstance(obj, list):
        return [serialize(item) for item in obj]
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj
