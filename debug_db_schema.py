import sqlite3
import os

# SQLite DBファイルのパス（FlaskのSQLALCHEMY_DATABASE_URIに合わせてください）
db_path = os.path.join('app', 'db', 'scart.db')

print(f"DBファイル: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("quotation_details テーブルのカラム一覧:")
cursor.execute("PRAGMA table_info(quotation_details);")
columns = cursor.fetchall()
for col in columns:
    # PRAGMA table_info の返り値: (cid, name, type, notnull, dflt_value, pk)
    print(f"  {col[1]} ({col[2]})")

conn.close()

print("\n実行方法: python debug_db_schema.py")
