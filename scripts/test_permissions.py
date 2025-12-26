# --- Logging buffer and debug() ---
import traceback
from pathlib import Path
import datetime
log_buffer = []
def debug(msg):
    log_buffer.append(str(msg))

# --- Project root and log path ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

def debug_dump_users():
    db_path = get_db_path()
    print(f"[DEBUG] db path={db_path}", flush=True)
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        print(f"[DEBUG] users table columns: {columns}", flush=True)
        # 候補列
        candidates = ["user_id", "username", "login", "login_id", "email", "name"]
        # パスワード系は絶対に表示しない
        pw_keywords = ["pass", "hash", "token", "salt"]
        safe_candidates = [c for c in candidates if not any(pw in c.lower() for pw in pw_keywords) and c in columns]
        if not safe_candidates:
            print(f"[DEBUG] no candidate login columns found in users table", flush=True)
            return
        # サンプル値
        col_str = ", ".join(safe_candidates)
        try:
            cur.execute(f"SELECT {col_str} FROM users LIMIT 10")
            rows = cur.fetchall()
            print(f"[DEBUG] users sample ({col_str}):", flush=True)
            for row in rows:
                print(f"[DEBUG]   {dict(zip(safe_candidates, row))}", flush=True)
        except Exception as e:
            print(f"[DEBUG] failed to fetch user samples: {e}", flush=True)
    finally:
        conn.close()
# scripts/test_permissions.py
import os
import sys
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re
import subprocess
import time

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "adminpass")
USER_USER = os.environ.get("USER_USER", "user")
USER_PASS = os.environ.get("USER_PASS", "userpass")
OTHER_USER = os.environ.get("OTHER_USER")
OTHER_PASS = os.environ.get("OTHER_PASS")

LOGIN_URL = BASE_URL + "/login"
CUSTOMERS_URL = BASE_URL + "/customers"
CUSTOMER_EDIT_URL = BASE_URL + "/customers/{id}/edit"
QUOTATION_NEW_URL = BASE_URL + "/quotation/new"

def print_result(results, label, ok, detail=None):
    results.append((label, ok, detail))
    msg = ("PASS" if ok else "FAIL") + ": " + label
    if detail:
        msg += f" [{detail}]"
    print(msg, flush=True)

def get_db_path() -> str:
    env_path = os.environ.get("SCART_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path1 = os.path.normpath(os.path.join(script_dir, "..", "estimates.db"))
    if os.path.exists(path1):
        return path1
    path2 = os.path.join(os.getcwd(), "estimates.db")
    if os.path.exists(path2):
        return path2
    raise FileNotFoundError("estimates.db not found (set SCART_DB_PATH or place estimates.db)")

def exit_if_fail(results) -> None:
    fails = [r for r in results if not r[1]]
    if fails:
        print("\nSome tests failed.")
        try:
            log_dir = PROJECT_ROOT / "artifacts" / "test_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"test_permissions_{ts}.log"
            with open(log_file, "w", encoding="utf-8") as f:
                # HEADER
                f.write(f"[HEADER] timestamp={ts}\n")
                f.write(f"[HEADER] BASE_URL={BASE_URL}\n")
                try:
                    db_path = get_db_path()
                except Exception as e:
                    db_path = f"ERROR: {e}"
                f.write(f"[HEADER] DB path={db_path}\n")
                f.write(f"[HEADER] python executable={sys.executable}\n")
                f.write(f"[HEADER] cwd={os.getcwd()}\n")
                # RESULTS
                f.write("[RESULTS]\n")
                for label, ok, detail in results:
                    f.write(f"  {'PASS' if ok else 'FAIL'}: {label} [{detail if detail else ''}]\n")
                # DEBUG
                f.write("[DEBUG]\n")
                for line in log_buffer:
                    if any(x in line.lower() for x in ["password", "password_hash", "token", "salt"]):
                        continue
                    f.write(f"  {line}\n")
                # EXCEPTION (if any)
                exc_type, exc_val, exc_tb = sys.exc_info()
                if exc_type:
                    f.write("[EXCEPTION]\n")
                    f.write("  " + "\n  ".join(traceback.format_exception(exc_type, exc_val, exc_tb)))
            print(f"[INFO] FAIL log saved: {log_file}")
            print(f"[INFO] FAIL log path: {log_file.resolve()}")
        except Exception as e:
            print(f"[ERROR] Could not write log: {e}")
        sys.exit(1)
    print("\nAll tests passed.")
    sys.exit(0)

def db_connect():
    return sqlite3.connect(get_db_path())

def detect_users_login_column(conn):
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        candidates = ["username", "user_name", "login", "login_id", "email", "name"]
        for c in candidates:
            if c in columns:
                return c
        return None
    except Exception:
        return None

def get_user_id_by_login(login_value):
    conn = db_connect()
    try:
        col = detect_users_login_column(conn)
        if not col:
            return None
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM users WHERE {col}=?", (login_value,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

class Session:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )

    def get_html(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = self.opener.open(req)
            body = resp.read().decode(errors="ignore")
            return resp.getcode(), body, resp.geturl()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            final_url = e.geturl() if hasattr(e, "geturl") else url
            return e.code, body, final_url

    def post_html(self, url: str, data: dict):
        encoded = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=encoded, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = self.opener.open(req)
            body = resp.read().decode(errors="ignore")
            return resp.getcode(), body, resp.geturl()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            final_url = e.geturl() if hasattr(e, "geturl") else url
            return e.code, body, final_url

    def find_csrf_token(self, html: str):
        for name in ("csrf_token", "_csrf_token", "csrf"):
            m = re.search(
                r'<input[^>]+type=["\']hidden["\'][^>]+name=["\']{}["\'][^>]*value=["\']([^"\']+)["\']'.format(
                    re.escape(name)
                ),
                html,
                re.I,
            )
            if m:
                return name, m.group(1)
        return None, None

    def find_login_fields(self, html: str):
        forms = re.findall(r'<form[^>]*>.*?</form>', html, re.I | re.DOTALL)
        user_priority = ["username","user","email","login","login_id","account","id"]
        for form in forms:
            m_pass = re.search(r'<input[^>]+type=["\']password["\'][^>]+name=["\']([^"\']+)["\']', form, re.I)
            if not m_pass:
                continue
            pass_field = m_pass.group(1)
            user_inputs = re.findall(r'<input[^>]+type=["\'](?:text|email)["\'][^>]+name=["\']([^"\']+)["\']', form, re.I)
            select_inputs = re.findall(r'<select[^>]+name=["\']([^"\']+)["\']', form, re.I)
            user_inputs = [u for u in user_inputs if "csrf" not in u.lower()]
            select_inputs = [s for s in select_inputs if "csrf" not in s.lower()]
            all_user_fields = user_inputs + select_inputs
            if not all_user_fields:
                continue
            for p in user_priority:
                for u in all_user_fields:
                    if p in u.lower():
                        user_field = u
                        break
                else:
                    continue
                break
            else:
                user_field = all_user_fields[0]
            m_action = re.search(r'<form[^>]*action=[\"\']([^\"\']+)[\"\']', form, re.I)
            action = m_action.group(1) if m_action else None
            return (user_field, pass_field, action, form, html)
        return ("username", "password", None, "", html)

    def parse_hidden_inputs(self, form_html, full_html):
        hidden = {}
        # from form_html
        for m in re.finditer(r'<input[^>]+type=[\"\']hidden[\"\'][^>]+name=[\"\']([^\"\']+)[\"\'][^>]*value=[\"\']([^\"\']*)[\"\']', form_html, re.I):
            name = m.group(1)
            value = m.group(2)
            hidden[name] = value
        # from full_html (for redundancy)
        for m in re.finditer(r'<input[^>]+type=[\"\']hidden[\"\'][^>]+name=[\"\']([^\"\']+)[\"\'][^>]*value=[\"\']([^\"\']*)[\"\']', full_html, re.I):
            name = m.group(1)
            value = m.group(2)
            hidden[name] = value
        return hidden

    def parse_select_options(self, form_html, full_html, select_name):
        # Try form_html first
        options = self._extract_select_options(form_html, select_name)
        if not options:
            options = self._extract_select_options(full_html, select_name)
        return options

    def _extract_select_options(self, html, select_name):
        # <select ... name="user_id" ...>...</select> or <select ... id="user_id" ...>...</select>
        select_pat = (
            r'<select[^>]+(?:name|id)=[\"\']?' + re.escape(select_name) + r'[\"\']?[^>]*>(.*?)</select>'
        )
        m = re.search(select_pat, html, re.I | re.DOTALL)
        if not m:
            return []
        select_block = m.group(1)
        options = []
        for opt in re.finditer(
            r'<option[^>]+value\\s*=\\s*([\"\']?)([^\"\'>\\s]+)\\1[^>]*>(.*?)</option>',
            select_block,
            re.I | re.DOTALL,
        ):
            value = opt.group(2)
            text = re.sub(r'<.*?>', '', opt.group(3)).strip()
            if value:
                options.append((value, text))
        # Also allow value=123 (no quotes)
        for opt in re.finditer(
            r'<option[^>]+value\\s*=\\s*([^\\s>]+)[^>]*>(.*?)</option>',
            select_block,
            re.I | re.DOTALL,
        ):
            value = opt.group(1).strip('\'"')
            text = re.sub(r'<.*?>', '', opt.group(2)).strip()
            if value and (value, text) not in options:
                options.append((value, text))
        return options

    def login(self, username: str, password: str) -> None:
        _, html, _ = self.get_html(LOGIN_URL)
        csrf_name, csrf_value = self.find_csrf_token(html)
        user_field, pass_field, action, form_html, full_html = self.find_login_fields(html)
        print(f"[DEBUG] login fields user={user_field} pass={pass_field} csrf={csrf_name} action={action}", flush=True)
        debug(f"[DEBUG] login fields user={user_field} pass={pass_field} csrf={csrf_name} action={action}")
        # form snippet debug
        snippet = ""
        if form_html:
            snippet = form_html[:500]
        else:
            idx = html.lower().find("user_id")
            if idx != -1:
                snippet = html[max(0, idx-250):idx+250]
        print(f"[DEBUG] login html snippet: {snippet}", flush=True)
        debug(f"[DEBUG] login html snippet: {snippet}")
        data = {}
        # hidden inputs
        data.update(self.parse_hidden_inputs(form_html, full_html))
        # 常に user_field へ username を送る（user_id でも例外なし）
        data[user_field] = username
        data[pass_field] = password
        if csrf_name and csrf_value:
            data[csrf_name] = csrf_value
        # POST先
        if action:
            if action.startswith("http"):
                post_url = action
            elif action.startswith("/"):
                post_url = BASE_URL.rstrip("/") + action
            else:
                post_url = BASE_URL.rstrip("/") + "/" + action
        else:
            post_url = LOGIN_URL
        print(f"[DEBUG] login POST data keys={list(data.keys())}", flush=True)
        debug(f"[DEBUG] login POST data keys={list(data.keys())}")
        post_code, post_body, post_url2 = self.post_html(post_url, data)
        # 抽出: bootstrap alert, flash messages, error messages
        alert_msgs = []
        # <div class="alert ...">...</div>
        for m in re.finditer(r'<div[^>]+class=["\"][^>]*alert[^>]*["\"][^>]*>(.*?)</div>', post_body, re.I | re.DOTALL):
            msg = re.sub(r'<.*?>', '', m.group(1)).strip()
            if msg:
                alert_msgs.append(msg)
        # flash/message/error クラス
        for m in re.finditer(r'<div[^>]+class=["\"][^>]*(message|error)[^>]*["\"][^>]*>(.*?)</div>', post_body, re.I | re.DOTALL):
            msg = re.sub(r'<.*?>', '', m.group(2)).strip()
            if msg and msg not in alert_msgs:
                alert_msgs.append(msg)
        if alert_msgs:
            print(f"[DEBUG] login POST alert/messages: {alert_msgs}", flush=True)
            debug(f"[DEBUG] login POST alert/messages: {alert_msgs}")
        else:
            print(f"[DEBUG] login POST response body head: {post_body[:400]}", flush=True)
            debug(f"[DEBUG] login POST response body head: {post_body[:400]}")
        # 成功判定: /customers へアクセスし /login でなければ成功
        code2, body, url2 = self.get_html(CUSTOMERS_URL)
        cookies_count = len(self.cj)
        print(f"[DEBUG] cookies count={cookies_count}", flush=True)
        debug(f"[DEBUG] cookies count={cookies_count}")
        if "/login" in url2:
            print(f"[DEBUG] after login redirected. url={url2} body={body[:400]}", flush=True)
            debug(f"[DEBUG] after login redirected. url={url2} body={body[:400]}")
            print(f"[DEBUG] login POST response code={post_code} url={post_url2}", flush=True)
            debug(f"[DEBUG] login POST response code={post_code} url={post_url2}")

def get_user_id(username: str):
    return get_user_id_by_login(username)

def create_pending_customer(requested_username: str) -> int:
    name = f"TestPendingUser_{int(time.time())}"
    name_kana = "テストペンディング"
    user_id = get_user_id(requested_username)
    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO customers (name, name_kana, status, requested_by_user_id) VALUES (?, ?, ?, ?)",
            (name, name_kana, "pending", user_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_approved_customer_id():
    conn = db_connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM customers WHERE status=? ORDER BY id DESC LIMIT 1",
            ("approved",),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def test_admin_login(results):
    sess = Session()
    sess.login(ADMIN_USER, ADMIN_PASS)
    code, _, url = sess.get_html(CUSTOMERS_URL)
    ok = (code == 200) and ("/login" not in url)
    detail = None if ok else f"HTTP {code} URL {url}"
    print_result(results, "Admin login", ok, detail)
    return sess

def test_user_login(results):
    sess = Session()
    sess.login(USER_USER, USER_PASS)
    code, _, url = sess.get_html(CUSTOMERS_URL)
    ok = (code == 200) and ("/login" not in url)
    detail = None if ok else f"HTTP {code} URL {url}"
    print_result(results, "User login", ok, detail)
    return sess

def test_edit_pending_customer(results, sess, cid: int, expect_200=True, label="Edit pending customer"):
    url = CUSTOMER_EDIT_URL.format(id=cid)
    code, _, final_url = sess.get_html(url)
    if expect_200:
        ok = (code == 200) and ("/login" not in final_url) and (f"/customers/{cid}/edit" in final_url)
    else:
        ok = f"/customers/{cid}/edit" not in final_url
    detail = None if ok else f"HTTP {code} URL {final_url}"
    print_result(results, f"{label} ({cid})", ok, detail)
    return ok

def test_other_user_edit_pending(results, cid: int):
    if not OTHER_USER or not OTHER_PASS:
        print_result(results, "Other user edit pending (SKIP)", True, "SKIP")
        return True
    sess = Session()
    sess.login(OTHER_USER, OTHER_PASS)
    return test_edit_pending_customer(results, sess, cid, expect_200=False, label="Other user edit pending")

def test_concurrent_approve(results):
    result = subprocess.run([sys.executable, "scripts/test_concurrent_approve.py"], capture_output=True)
    ok = result.returncode == 0
    detail = None
    if not ok:
        out = result.stdout.decode(errors="ignore")
        err = result.stderr.decode(errors="ignore")
        detail = f"stdout: {out[:1000]} stderr: {err[:1000]}"
    print_result(results, "Concurrent approve audit log", ok, detail)
    return ok

def test_quotation_new(results, sess, approved_cid: int, pending_cid: int):
    code, html, url = sess.get_html(QUOTATION_NEW_URL)
    pattern1 = f'value="{approved_cid}"'
    pattern2 = f"value='{approved_cid}'"
    ok_get = (code == 200) and ("/login" not in url) and ((pattern1 in html) or (pattern2 in html))
    detail_get = None if ok_get else f"HTTP {code} URL {url} BODY:{html[:200]}"
    print_result(results, "Quotation new GET: approved customer in list", ok_get, detail_get)
    csrf_name, csrf_value = sess.find_csrf_token(html)
    data = {
        "company_name": "TestCompany",
        "project_name": "TestProject",
        "customer_id": str(pending_cid),
        "contact_name": "",
        "delivery_date": "",
        "delivery_terms": "",
        "payment_terms": "",
        "valid_until": "",
        "remarks": "",
        "estimator_name": "",
        "discount_rate": "0",
        "distance_m": "",
        "intersection_count": "",
        "station_count": "",
        "vehicle_count": "",
        "equipment_count": "",
        "circuit_difficulty": "",
    }
    if csrf_name and csrf_value:
        data[csrf_name] = csrf_value
    post_code, post_html, post_url = sess.post_html(QUOTATION_NEW_URL, data)
    blocked = ("未承認" in post_html) or ("承認後" in post_html) or ("見積を登録しました" not in post_html)
    detail_post = None if blocked else f"HTTP {post_code} URL {post_url} BODY:{post_html[:200]}"
    print_result(results, "Quotation new POST: pending customer blocked", blocked, detail_post)
    return ok_get and blocked

def main(results):
    db_path = get_db_path()
    print(f"[DEBUG] cwd={os.getcwd()}", flush=True)
    print(f"[DEBUG] db path={db_path}", flush=True)
    if os.environ.get("DUMP_USERS") == "1":
        debug_dump_users()
        sys.exit(0)
    print("[DEBUG] start test_permissions", flush=True)
    admin_sess = test_admin_login(results)
    user_sess = test_user_login(results)
    pending_cid = create_pending_customer(USER_USER)
    print_result(results, "Create pending customer", True, f"id={pending_cid}")
    approved_cid = get_approved_customer_id()
    if not approved_cid:
        print_result(results, "No approved customer found", False, "Need at least one approved customer in DB")
        exit_if_fail(results)
    test_edit_pending_customer(results, user_sess, pending_cid, expect_200=True, label="User edit pending")
    test_edit_pending_customer(results, admin_sess, pending_cid, expect_200=True, label="Admin edit pending")
    test_other_user_edit_pending(results, pending_cid)
    test_concurrent_approve(results)
    test_quotation_new(results, admin_sess, approved_cid, pending_cid)
    exit_if_fail(results)

if __name__ == "__main__":
    results = []
    try:
        main(results)
    except Exception as e:
        debug(traceback.format_exc())
        results.append(("Unhandled exception", False, f"{type(e).__name__}: {e}"))
        exit_if_fail(results)


