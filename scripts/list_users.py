print("### LIST_USERS_V3 ###")

import os
import sqlite3
import sys

def main():
    db_path = os.environ.get("SCART_DB_PATH", "estimates.db")
    print(f"[INFO] DB={db_path}")

    conn = sqlite3.connect(db_path, timeout=10)
    try:
        cur = conn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
        print(f"[INFO] users.columns={cols}")

        if "login_id" in cols:
            sql = "SELECT id, login_id, display_name, role, is_active FROM users ORDER BY id"
        elif "user_id" in cols and "name" in cols:
            sql = "SELECT id, user_id, name, role, is_active FROM users ORDER BY id"
        else:
            sql = "SELECT * FROM users ORDER BY 1"

        rows = cur.execute(sql).fetchall()
        print(f"[INFO] users.count={len(rows)}")
        for r in rows:
            print(r)
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
