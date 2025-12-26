import sqlite3
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "estimates.db"

if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# users table
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE,
    name TEXT,
    password_hash TEXT,
    role TEXT,
    is_active INTEGER,
    created_at TEXT,
    updated_at TEXT
)
""")

# customers table
c.execute("""
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    name_kana TEXT,
    status TEXT,
    requested_by_user_id INTEGER
)
""")

# customer_approval_log table
c.execute("""
CREATE TABLE customer_approval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    action TEXT,
    actor_user_id INTEGER,
    created_at TEXT
)
""")

# Seed users
import datetime
now = datetime.datetime.now().isoformat()
users = [
    ("admin", "管理者", "adminpass", "admin", 1, now, now),
    ("user", "一般ユーザー", "userpass", "user", 1, now, now)
]
c.executemany("INSERT INTO users (user_id, name, password_hash, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", users)

# Get user id for 'user'
c.execute("SELECT id FROM users WHERE user_id=?", ("user",))
user_row = c.fetchone()
user_id = user_row[0] if user_row else 2

# Seed customers (approved and pending)
customers = [
    ("Approved Customer", "承認済み顧客", "approved", user_id),
    ("Pending Customer", "ペンディング顧客", "pending", user_id)
]
c.executemany("INSERT INTO customers (name, name_kana, status, requested_by_user_id) VALUES (?, ?, ?, ?)", customers)

conn.commit()
conn.close()

print(f"[INFO] seeded db: {DB_PATH.resolve()}")
