import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# 見積16のデータを確認
cursor.execute('SELECT id, original_id, revision_no, quotation_no, company_name, created_at FROM quotations WHERE id = 16')
row = cursor.fetchone()
if row:
    print(f'見積ID 16:')
    print(f'  original_id: {row[1]}')
    print(f'  revision_no: {row[2]}')
    print(f'  quotation_no: {row[3]}')
    print(f'  company_name: {row[4]}')
    print(f'  created_at: {row[5]}')
else:
    print('見積ID 16 が見つかりません')

# quotation_no のカラムが存在するか確認
cursor.execute("PRAGMA table_info(quotations)")
columns = cursor.fetchall()
print(f'\nquotations テーブルのカラム:')
for col in columns:
    if 'quotation_no' in col[1]:
        print(f'  {col[1]} ({col[2]})')

conn.close()
