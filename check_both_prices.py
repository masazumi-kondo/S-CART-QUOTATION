#!/usr/bin/env python3
import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'estimates.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get latest quotation  
cursor.execute('''
    SELECT id, quotation_no, company_name
    FROM quotations
    ORDER BY id DESC
    LIMIT 1
''')

latest = cursor.fetchone()

if latest:
    qid, qno, company = latest
    print(f'Latest quotation: ID={qid}, {qno}, {company}\n')
    
    # Query with BOTH unit_price AND price columns
    cursor.execute('''
        SELECT id, description, unit_price, price, subtotal, cost
        FROM quotation_details
        WHERE quotation_id = ? AND (description LIKE '%自動算出%' OR description LIKE '%V2%')
    ''', (qid,))
    
    v2_details = cursor.fetchall()
    print(f'V2 rows found: {len(v2_details)}\n')
    print('Comparison:')
    for id, desc, unit_price, price, subtotal, cost in v2_details:
        print(f'{desc}:')
        print(f'  unit_price (old column): {unit_price}')
        print(f'  price (new column): {price}')
        print(f'  subtotal: {subtotal}')
        print(f'  cost: {cost}')
        print()

conn.close()
