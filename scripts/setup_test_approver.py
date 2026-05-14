#!/usr/bin/env python
"""Setup test users for Phase 6 permission testing"""

import sqlite3
import os
from werkzeug.security import generate_password_hash


def get_db_path():
    env_db = os.environ.get("SCART_DB_PATH")
    if env_db:
        return env_db
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "estimates.db")


def upsert_user(conn, login_id, password, role):
    """Create or update a user"""
    password_hash = generate_password_hash(password)
    
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE login_id = ?", (login_id,))
    row = cur.fetchone()
    
    if row:
        cur.execute(
            "UPDATE users SET password_hash=?, is_active=1, role=? WHERE login_id=?",
            (password_hash, role, login_id)
        )
        print(f"[OK] User '{login_id}' updated (role={role})")
    else:
        display_name_map = {
            "admin": "管理者",
            "approver": "承認者",
            "user": "一般ユーザー"
        }
        display_name = display_name_map.get(role, role)
        cur.execute(
            "INSERT INTO users (login_id, display_name, password_hash, role, is_active, receive_notifications) VALUES (?, ?, ?, ?, 1, 1)",
            (login_id, display_name, password_hash, role)
        )
        print(f"[OK] User '{login_id}' created (role={role})")
    
    conn.commit()


def main():
    db_path = get_db_path()
    print(f"[INFO] DB path: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        # Create admin (if not exists)
        upsert_user(conn, "admin", "admin123", "admin")
        
        # Create approver
        upsert_user(conn, "approver", "approver123", "approver")
        
        # Create general user
        upsert_user(conn, "user", "user123", "user")
        
        print("[INFO] Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
