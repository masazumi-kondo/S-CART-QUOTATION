import os
import sqlite3
import sys

REQUIRED = {"login_id", "display_name", "password_hash"}

def main() -> int:
    db_path = os.environ.get("SCART_DB_PATH") or "estimates.db"

    if not os.path.exists(db_path):
        print(f"[FAIL] DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(db_path, timeout=30)
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            print("[FAIL] users table not found")
            return 3

        cur = conn.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur.fetchall()}
        missing = sorted(list(REQUIRED - cols))
        if missing:
            print(f"[FAIL] users schema missing columns: {missing}")
            print(f"[DIAG] existing columns: {sorted(list(cols))}")
            return 4

        print("[OK] users schema guard passed")
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
