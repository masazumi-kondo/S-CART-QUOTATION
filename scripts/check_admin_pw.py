import sqlite3
from werkzeug.security import check_password_hash

db_path = r"C:\Users\3950\SCART Quotation\estimates.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT password_hash FROM users WHERE login_id='admin'")
row = cur.fetchone()
if not row:
    print("admin not found")
else:
    h = row[0]
    print("hash head:", h[:30])
    print("check(admin1234):", check_password_hash(h, "admin1234"))

conn.close()
