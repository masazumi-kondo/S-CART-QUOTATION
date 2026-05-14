#!/usr/bin/env python
"""Test the approver user role"""

import sqlite3
import os

def get_db_path():
    env_db = os.environ.get("SCART_DB_PATH")
    if env_db:
        return env_db
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "estimates.db")


def check_user_roles():
    """Check user roles in database"""
    db_path = get_db_path()
    print(f"[INFO] DB path: {db_path}")
    
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, login_id, role, is_active FROM users WHERE login_id IN ('admin', 'approver', 'user')")
        rows = cur.fetchall()
        
        if not rows:
            print("[ERROR] No users found")
            return
        
        print("[INFO] Current users:")
        for user_id, login_id, role, is_active in rows:
            print(f"  - {login_id}: role={role}, is_active={is_active}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_user_roles()
