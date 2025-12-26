import sqlite3
from pprint import pprint

db_path = "estimates.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== tables ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
pprint(cur.fetchall())

print("\n=== customer_approval_log columns ===")
cur.execute("PRAGMA table_info(customer_approval_log)")
pprint(cur.fetchall())

print("\n=== legacy tables like customer_approval_log_legacy ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'customer_approval_log_legacy_%' ORDER BY name")
pprint(cur.fetchall())

conn.close()
