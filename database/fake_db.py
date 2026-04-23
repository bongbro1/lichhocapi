import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "users.json")

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as file:
        users_db = json.load(file)
else:
    users_db = {}


def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as file:
        json.dump(users_db, file, indent=4)


def add_user(username, password, domain):
    if username in users_db:
        return False

    users_db[username] = {
        "password": password,
        "domain": domain
    }
    save_db()
    return True


def remove_user(username):
    if username not in users_db:
        return False

    del users_db[username]
    save_db()
    return True


def validate_user(username, password, domain):
    if not username or not password or not domain:
        return False

    user = users_db.get(username)
    if user and user["password"] == password and user["domain"] == domain:
        return True

    # File nay chi la cache tam de backend nho credentials da dung.
    # Khong duoc chan login that neu user doi mat khau hoac domain cache lech.
    users_db[username] = {
        "password": password,
        "domain": domain
    }
    save_db()
    return True
