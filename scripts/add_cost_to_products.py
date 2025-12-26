import sqlite3

db_path = "app/db/estimates.db"  # 実際のパスに合わせて修正
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("ALTER TABLE products ADD COLUMN cost REAL DEFAULT 0")
conn.commit()
conn.close()
print("productsテーブルに cost カラムを追加しました。")
