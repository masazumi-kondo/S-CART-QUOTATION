import sqlite3

db_path = "dist/SCART_Quotation/estimates.db"  # ←あなたの環境に合わせて

conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE quotations ADD COLUMN discount_rate REAL DEFAULT 0;")
    print("カラム discount_rate を追加しました。")
except Exception as e:
    print("既に追加済み、またはエラー:", e)

conn.commit()
conn.close()
