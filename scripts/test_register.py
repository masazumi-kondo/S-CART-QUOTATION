import os
import sqlite3
import requests
import time

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
DB_PATH = os.environ.get("SCART_DB_PATH", "estimates.db")

LOGIN_ID = "testuser1"
DISPLAY_NAME = "テストユーザー"
PASSWORD = "testpass123"

# 1. /register にPOST
for i in range(10):
    try:
        resp = requests.post(f"{BASE_URL}/register", data={
            "login_id": LOGIN_ID,
            "display_name": DISPLAY_NAME,
            "password": PASSWORD
        }, timeout=5)
        if resp.status_code in (200, 302):
            break
    except Exception as e:
        time.sleep(1)
else:
    print("[ERROR] /register POST失敗")
    exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT login_id, display_name, is_active FROM users WHERE login_id=?", (LOGIN_ID,))
    row = cur.fetchone()
    conn.close()
    if not row:
        print("[ERROR] usersテーブルに登録がありません")
        exit(2)
    if row[2] not in (0, False):
        print(f"[ERROR] is_active={row[2]} (承認待ちで登録されていません)")
        exit(3)
    print(f"[OK] 登録確認: login_id={row[0]}, display_name={row[1]}, is_active={row[2]}")
except Exception as e:
    print(f"[ERROR] DB確認失敗: {e}")
    exit(3)
