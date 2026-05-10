#!/usr/bin/env python3
import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'estimates.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get last 5 quotations
cursor.execute('''
    SELECT id, quotation_no, company_name, created_at
    FROM quotations
    ORDER BY id DESC
    LIMIT 5
''')

quotations = cursor.fetchall()
print(f'Recent quotations: {len(quotations)}\n')
for q in quotations:
    qid, qno, company, created = q
    print(f'ID:{qid} | {qno} | {company} | {created}')

conn.close()
