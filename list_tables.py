import sqlite3

db_path = "dist/SCART_Quotation/estimates.db"  # 実際のDBパスに合わせて
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("テーブル一覧:", tables)

conn.close()
