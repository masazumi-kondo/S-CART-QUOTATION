import os
import sqlite3
import sys

def get_db_path():
    p = os.environ.get("SCART_DB_PATH")
    if p:
        return p
    return "estimates.db"

def table_info(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]  # column names

def main():
    db_path = get_db_path()
    print(f"[INFO] DB={db_path}")

    conn = sqlite3.connect(db_path, timeout=10)
    try:
        cols = table_info(conn, "users")
        print(f"[INFO] users.columns={cols}")

        # 旧/新スキーマ両対応で表示
        if "login_id" in cols:
            sql = "SELECT id, login_id, display_name, role, is_active FROM users ORDER BY id"
        elif "user_id" in cols and "name" in cols:
            # 旧スキーマ想定
            sql = "SELECT id, user_id, name, role, is_active FROM users ORDER BY id"
        else:
            # 最低限: 全列を見る
            sql = "SELECT * FROM users ORDER BY 1"

        cur = conn.execute(sql)
        rows = cur.fetchall()

        print(f"[INFO] users.count={len(rows)}")
        for r in rows:
            print(r)

        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
