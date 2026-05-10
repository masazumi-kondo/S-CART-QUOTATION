import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# テーブル一覧
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('テーブル一覧:')
for table in tables:
    print(f'  - {table[0]}')

# 削除された見積1のdetailsが残っていないか確認
cursor.execute('SELECT COUNT(*) FROM quotation_details WHERE quotation_id = 1')
count = cursor.fetchone()[0]
print(f'\n見積ID 1 の detail 件数: {count}')

# 見積1 自体が削除されたか確認
cursor.execute('SELECT COUNT(*) FROM quotations WHERE id = 1')
count = cursor.fetchone()[0]
print(f'見積ID 1 自体: {count}')

# 現在の見積総数
cursor.execute('SELECT COUNT(*) FROM quotations')
count = cursor.fetchone()[0]
print(f'現在の見積総数: {count}')

# 見積一覧
cursor.execute('SELECT id, original_id, revision_no FROM quotations ORDER BY id DESC')
rows = cursor.fetchall()
print(f'\n現在の見積データ:')
for row in rows:
    print(f'  ID: {row[0]}, original_id: {row[1]}, revision_no: {row[2]}')

conn.close()
