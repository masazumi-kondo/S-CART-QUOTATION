import sqlite3
conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()
cursor.execute('SELECT id, quotation_no, approval_status FROM quotations WHERE approval_status = "pending" LIMIT 5')
pending = cursor.fetchall()
for q in pending:
    print(f'ID: {q[0]}, No: {q[1]}, Status: {q[2]}')
conn.close()
