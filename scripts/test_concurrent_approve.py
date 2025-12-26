# scripts/test_concurrent_approve.py
import os
import sys
import sqlite3
import threading
import time
import requests
import traceback
from pathlib import Path
import datetime
import platform

# --- Project root and log path ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOG_DIR = PROJECT_ROOT / "artifacts" / "test_logs"

# --- Logging buffer and debug() ---
log_buffer = []
def debug(msg):
    log_buffer.append(str(msg))

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "adminpass")

LOGIN_URL = BASE_URL.rstrip("/") + "/login"


def get_db_path() -> str:
    env_path = os.environ.get("SCART_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    path1 = PROJECT_ROOT / "estimates.db"
    if path1.exists():
        return str(path1)
    path2 = Path(os.getcwd()) / "estimates.db"
    if path2.exists():
        return str(path2)
    raise FileNotFoundError("estimates.db not found (set SCART_DB_PATH or place estimates.db)")

def filter_sensitive(line):
    # Remove lines containing sensitive keywords
    keywords = ["password", "password_hash", "token", "salt"]
    for k in keywords:
        if k in line.lower():
            return False
    return True


def db_connect():
    return sqlite3.connect(get_db_path())


def login_admin(sess: requests.Session) -> None:
    # あなたの login フォームは user_id / password
    r = sess.post(
        LOGIN_URL,
        data={"user_id": ADMIN_USER, "password": ADMIN_PASS},
        allow_redirects=True,
        timeout=10,
    )
    # 成功していれば session cookie が入るはず
    if not sess.cookies:
        raise RuntimeError(f"Login failed (no cookies). status={r.status_code} url={r.url}")


def create_pending_customer_via_db() -> int:
    """
    HTTP 経由だと参照DBがズレる可能性があるため、DB直INSERTで pending顧客を作る。
    """
    conn = db_connect()
    try:
        cur = conn.cursor()

        # customers の列一覧
        cur.execute("PRAGMA table_info(customers)")
        columns = [row[1] for row in cur.fetchall()]
        if not columns:
            raise RuntimeError("customers table not found or has no columns")

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        customer_data = {}
        # 必須っぽい列だけ確実に入れる（存在する列のみ）
        if "name" in columns:
            customer_data["name"] = f"承認競合テスト顧客_{int(time.time())}"
        if "name_kana" in columns:
            customer_data["name_kana"] = "ショウニンキョウゴウテスト"
        if "status" in columns:
            customer_data["status"] = "pending"
        if "created_at" in columns:
            customer_data["created_at"] = now
        if "updated_at" in columns:
            customer_data["updated_at"] = now

        # 任意列（存在すれば埋める）
        fixed_map = {
            "customer_code": "TST001",
            "postal_code": "100-0001",
            "address": "東京都千代田区1-1-1",
            "phone": "03-0000-0000",
            "transaction_type": "直接取引",
            "payment_terms": "末締翌月末払い",
            "note": "承認競合テスト用",
        }
        for k, v in fixed_map.items():
            if k in columns:
                customer_data[k] = v

        # requested_by_user_id があれば admin の users.id を入れる
        if "requested_by_user_id" in columns:
            cur.execute("SELECT id FROM users WHERE user_id=?", (ADMIN_USER,))
            row = cur.fetchone()
            if row:
                customer_data["requested_by_user_id"] = row[0]

        if not customer_data:
            raise RuntimeError("No insertable columns found in customers")

        col_names = ", ".join(customer_data.keys())
        q_marks = ", ".join(["?"] * len(customer_data))
        values = list(customer_data.values())

        cur.execute(f"INSERT INTO customers ({col_names}) VALUES ({q_marks})", values)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def find_approval_log_table(conn: sqlite3.Connection) -> str | None:
    """
    監査ログテーブル名が環境差分になる可能性があるため、自動探索する。
    - 優先: customer_approval_log / customer_approval_logs
    - それ以外: customers + approve/log を含むテーブル
    """
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]

    for name in ("customer_approval_log", "customer_approval_logs"):
        if name in tables:
            return name

    # ゆるく探索
    candidates = []
    for t in tables:
        tl = t.lower()
        if "customer" in tl and ("approve" in tl or "approval" in tl) and ("log" in tl or "audit" in tl):
            candidates.append(t)
    return candidates[0] if candidates else None


def get_approval_log_count(customer_id: int) -> int | None:
    conn = db_connect()
    try:
        table = find_approval_log_table(conn)
        if not table:
            return None
        cur = conn.cursor()
        # customer_id 列がある前提（なければ None 扱い）
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if "customer_id" not in cols:
            return None
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE customer_id=?", (customer_id,))
        return int(cur.fetchone()[0])
    finally:
        conn.close()


def get_customer_status(customer_id: int) -> str:
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM customers WHERE id=?", (customer_id,))
        row = cur.fetchone()
        if not row:
            raise Exception("Customer not found in DB")
        return row[0]
    finally:
        conn.close()


def approve_customer(sess: requests.Session, customer_id: int, results: list, idx: int) -> None:
    """
    approve エンドポイントは実装により差分があり得るため、
    まず /customers/<id>/approve を試し、ダメなら /customers/<id>/edit から POST する運用に合わせて修正してください。
    """
    try:
        url = f"{BASE_URL.rstrip('/')}/customers/{customer_id}/approve"
        r = sess.post(url, data={"approval_comment": f"approve-{idx}"}, allow_redirects=False, timeout=10)
        results[idx] = (r.status_code, r.headers.get("Location", ""))
        debug(f"[DEBUG] approve_customer idx={idx} status={r.status_code} location={r.headers.get('Location','')}")
    except Exception as e:
        results[idx] = ("EXC", str(e))
        debug(f"[DEBUG] approve_customer idx={idx} EXC: {e}")



def main() -> int:
    # Header info
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    header = {
        "timestamp": ts,
        "BASE_URL": BASE_URL if BASE_URL else "N/A",
        "DB_path": None,
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "platform": platform.platform(),
    }
    try:
        header["DB_path"] = get_db_path()
    except Exception as e:
        header["DB_path"] = f"ERROR: {e}"
    debug(f"[DEBUG] BASE_URL={header['BASE_URL']}")
    debug(f"[DEBUG] DB={header['DB_path']}")
    print(f"[INFO] BASE_URL={header['BASE_URL']}")
    print(f"[INFO] DB={header['DB_path']}")

    # Scenario info
    scenario = {}
    scenario["threads"] = 2
    scenario["processes"] = 1

    # 監査ログの事前件数（テーブルが見つからない場合は None）
    before_count = None

    sess1 = requests.Session()
    sess2 = requests.Session()
    login_admin(sess1)
    login_admin(sess2)

    customer_id = create_pending_customer_via_db()
    scenario["customer_id"] = customer_id
    print(f"[INFO] Created pending customer id={customer_id}")
    debug(f"[DEBUG] Created pending customer id={customer_id}")

    # 作成直後に存在確認（ここで落ちるなら DBパスが違う）
    try:
        _ = get_customer_status(customer_id)
    except Exception as e:
        debug(f"[DEBUG] get_customer_status EXC: {e}")
        return exit_if_fail([("Customer status check", False, str(e))], header, scenario)

    before_count = get_approval_log_count(customer_id)
    if before_count is None:
        print("[WARN] Approval log table not found or unsupported; will skip log count assertion")
        debug("[WARN] Approval log table not found or unsupported; will skip log count assertion")

    results = []
    approve_results = [None, None]
    t1 = threading.Thread(target=approve_customer, args=(sess1, customer_id, approve_results, 0))
    t2 = threading.Thread(target=approve_customer, args=(sess2, customer_id, approve_results, 1))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"[INFO] approve results: {approve_results}")
    debug(f"[DEBUG] approve results: {approve_results}")
    # Collect results
    for idx, r in enumerate(approve_results):
        ok = isinstance(r, tuple) and r[0] == 200
        label = f"approve_customer_thread_{idx}"
        detail = str(r)
        results.append((label, ok, detail))

    # 最終 status が approved になっているか
    try:
        status = get_customer_status(customer_id)
        print(f"[INFO] final customer status: {status}")
        debug(f"[DEBUG] final customer status: {status}")
    except Exception as e:
        debug(f"[DEBUG] get_customer_status final EXC: {e}")
        return exit_if_fail(results + [("Final customer status", False, str(e))], header, scenario)

    if status != "approved":
        print("[FAIL] customer status is not approved")
        debug("[FAIL] customer status is not approved")
        results.append(("Customer status is approved", False, f"status={status}"))
        return exit_if_fail(results, header, scenario)
    else:
        results.append(("Customer status is approved", True, f"status={status}"))

    after_count = get_approval_log_count(customer_id)
    if before_count is not None and after_count is not None:
        delta = after_count - before_count
        print(f"[INFO] approval log delta: {delta} (before={before_count}, after={after_count})")
        debug(f"[DEBUG] approval log delta: {delta} (before={before_count}, after={after_count})")
        ok = delta == 1
        label = "Approval log count delta"
        detail = f"delta={delta} (before={before_count}, after={after_count})"
        results.append((label, ok, detail))
        if not ok:
            print("[FAIL] approval log count delta is not 1")
            debug("[FAIL] approval log count delta is not 1")
            return exit_if_fail(results, header, scenario)

    # Summary
    pass_count = sum(1 for r in results if r[1])
    fail_count = sum(1 for r in results if not r[1])
    print(f"[PASS] concurrent approve test passed")
    debug(f"[PASS] concurrent approve test passed")
    print(f"TOTAL: {pass_count} PASS, {fail_count} FAIL")
    debug(f"TOTAL: {pass_count} PASS, {fail_count} FAIL")
    if fail_count:
        return exit_if_fail(results, header, scenario)
    return 0

def exit_if_fail(results, header, scenario):
    fails = [r for r in results if not r[1]]
    if not fails:
        return 0
    # --- log file output ---
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = header["timestamp"]
        log_file = LOG_DIR / f"test_concurrent_approve_{ts}.log"
        with open(log_file, "w", encoding="utf-8") as f:
            # HEADER
            f.write(f"[HEADER] timestamp={header['timestamp']}\n")
            f.write(f"[HEADER] BASE_URL={header['BASE_URL']}\n")
            f.write(f"[HEADER] DB path={header['DB_path']}\n")
            f.write(f"[HEADER] python executable={header['python_executable']}\n")
            f.write(f"[HEADER] cwd={header['cwd']}\n")
            f.write(f"[HEADER] platform={header['platform']}\n")
            # SCENARIO
            f.write(f"[SCENARIO] threads={scenario.get('threads','N/A')} processes={scenario.get('processes','N/A')} customer_id={scenario.get('customer_id','N/A')}\n")
            # RESULTS
            f.write("[RESULTS]\n")
            for label, ok, detail in results:
                f.write(f"  {'PASS' if ok else 'FAIL'}: {label} [{detail if detail else ''}]\n")
            pass_count = sum(1 for r in results if r[1])
            fail_count = sum(1 for r in results if not r[1])
            f.write(f"TOTAL: {pass_count} PASS, {fail_count} FAIL\n")
            # DEBUG
            f.write("[DEBUG]\n")
            for line in log_buffer:
                if filter_sensitive(line):
                    f.write(f"  {line}\n")
            # EXCEPTION
            exc_type, exc_val, exc_tb = sys.exc_info()
            if exc_type:
                f.write("[EXCEPTION]\n")
                f.write("  " + "\n  ".join(traceback.format_exception(exc_type, exc_val, exc_tb)))
        print(f"[INFO] FAIL log saved: {log_file}")
        print(f"[INFO] FAIL log path: {log_file.resolve()}")
    except Exception as e:
        print(f"[ERROR] Could not write log: {e}")
    sys.exit(1)


if __name__ == "__main__":
    results = []
    header = None
    scenario = None
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        header = {
            "timestamp": ts,
            "BASE_URL": BASE_URL if BASE_URL else "N/A",
            "DB_path": None,
            "python_executable": sys.executable,
            "cwd": os.getcwd(),
            "platform": platform.platform(),
        }
        try:
            header["DB_path"] = get_db_path()
        except Exception as e:
            header["DB_path"] = f"ERROR: {e}"
        scenario = {"threads": 2, "processes": 1}
        main_result = main()
        sys.exit(main_result)
    except Exception as e:
        debug(traceback.format_exc())
        results.append(("Unhandled exception", False, f"{type(e).__name__}: {e}"))
        if header is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            header = {
                "timestamp": ts,
                "BASE_URL": BASE_URL if BASE_URL else "N/A",
                "DB_path": f"ERROR: {e}",
                "python_executable": sys.executable,
                "cwd": os.getcwd(),
                "platform": platform.platform(),
            }
        if scenario is None:
            scenario = {"threads": 2, "processes": 1}
        exit_if_fail(results, header, scenario)
