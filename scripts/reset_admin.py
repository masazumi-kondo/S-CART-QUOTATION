import sqlite3
from werkzeug.security import generate_password_hash

db_path = r"estimates.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# admin が無ければ作る／あれば更新
pw = generate_password_hash("admin1234")

cur.execute("SELECT id FROM users WHERE login_id = ?", ("admin",))
row = cur.fetchone()

if row is None:
    cur.execute(
        "INSERT INTO users (login_id, display_name, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)",
        ("admin", "管理者", pw, "admin", 1)
    )
    print("[OK] admin user created (admin / admin1234)")
else:
    cur.execute(
        "UPDATE users SET password_hash=?, is_active=1, role='admin' WHERE login_id=?",
        (pw, "admin")
    )
    print("[OK] admin user updated (admin / admin1234) and activated")

conn.commit()
conn.close()
