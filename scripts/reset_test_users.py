import os
import sys
import sqlite3
import datetime
from werkzeug.security import generate_password_hash

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

def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]

def upsert_user(conn, user_id, password, role):
    columns = get_columns(conn, "users")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hash_val = generate_password_hash(password)
    cur = conn.cursor()
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        set_cols = []
        params = []
        if "password_hash" in columns:
            set_cols.append("password_hash=?")
            params.append(hash_val)
        if "is_active" in columns:
            set_cols.append("is_active=1")
        if "role" in columns:
            set_cols.append("role=?")
            params.append(role)
        if "updated_at" in columns:
            set_cols.append("updated_at=?")
            params.append(now)
        set_clause = ", ".join(set_cols)
        params.append(user_id)
        sql = f"UPDATE users SET {set_clause} WHERE user_id=?"
        cur.execute(sql, params)
        print(f"[INFO] Updated user_id={user_id}")
    else:
        insert_cols = ["user_id"]
        insert_vals = [user_id]
        if "password_hash" in columns:
            insert_cols.append("password_hash")
            insert_vals.append(hash_val)
        if "is_active" in columns:
            insert_cols.append("is_active")
            insert_vals.append(1)
        if "role" in columns:
            insert_cols.append("role")
            insert_vals.append(role)
        if "created_at" in columns:
            insert_cols.append("created_at")
            insert_vals.append(now)
        if "updated_at" in columns:
            insert_cols.append("updated_at")
            insert_vals.append(now)
        if "name" in columns:
            insert_cols.append("name")
            insert_vals.append(user_id)
        col_str = ", ".join(insert_cols)
        q_str = ", ".join(["?" for _ in insert_cols])
        sql = f"INSERT INTO users ({col_str}) VALUES ({q_str})"
        cur.execute(sql, insert_vals)
        print(f"[INFO] Created user_id={user_id}")
    conn.commit()

def main():
    db_path = get_db_path()
    print(f"[INFO] DB path: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        upsert_user(conn, "admin", "adminpass", "admin")
        upsert_user(conn, "user", "userpass", "user")
    finally:
        conn.close()
    print("[INFO] Done.")

if __name__ == "__main__":
    main()
