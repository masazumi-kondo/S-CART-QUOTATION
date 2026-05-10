#!/usr/bin/env python3
import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'estimates.db')
print(f'Using database: {db_path}')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get latest 3 quotations
cursor.execute('SELECT id, quotation_no, company_name FROM quotation ORDER BY id DESC LIMIT 3')
quotations = cursor.fetchall()

for q in quotations:
    qid, qno, company = q
    print(f'\n=== Quotation ID:{qid} ({qno}) - {company} ===')
    
    cursor.execute('''
        SELECT id, description, unit_price, quantity, subtotal, cost
        FROM quotation_details
        WHERE quotation_id = ?
        ORDER BY id
    ''', (qid,))
    
    details = cursor.fetchall()
    for d in details:
        did, desc, unit_price, qty, subtotal, cost = d
        is_v2 = '自動算出' in desc
        marker = ' [V2]' if is_v2 else ''
        print(f'  {did}: {desc}{marker}')
        print(f'     unit_price={unit_price}, qty={qty}, subtotal={subtotal}, cost={cost}')

conn.close()
