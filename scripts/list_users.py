import sqlite3
from pprint import pprint

db_path = r"estimates.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT id, login_id, display_name, role, is_active FROM users ORDER BY id")
print("=== users ===")
pprint(cur.fetchall())

conn.close()
