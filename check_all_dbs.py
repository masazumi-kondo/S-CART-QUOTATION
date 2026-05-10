#!/usr/bin/env python3
import sqlite3
import os

# Check both database paths
paths = {
    'estimates.db': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'estimates.db'),
    'app/db/scart.db': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/db/scart.db'),
}

for name, path in paths.items():
    print(f'\n=== {name} ({path}) ===')
    if not os.path.exists(path):
        print('FILE NOT FOUND')
        continue
    
    file_size = os.path.getsize(path)
    print(f'File size: {file_size} bytes')
    
    if file_size == 0:
        print('File is empty')
        continue
    
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')
        
        # Try to get latest quotation
        try:
            cursor.execute('SELECT id, quotation_no, company_name FROM quotations ORDER BY id DESC LIMIT 1')
            latest = cursor.fetchone()
            if latest:
                qid, qno, company = latest
                print(f'Latest quotation: ID={qid}, No={qno}, Company={company}')
                
                # Get details for this quotation
                cursor.execute('''
                    SELECT description, unit_price, subtotal, cost
                    FROM quotation_details
                    WHERE quotation_id = ? AND (description LIKE '%自動算出%' OR description LIKE '%V2%')
                ''', (qid,))
                v2_details = cursor.fetchall()
                print(f'V2 rows found: {len(v2_details)}')
                for desc, unit_price, subtotal, cost in v2_details:
                    print(f'  - {desc}: unit_price={unit_price}, subtotal={subtotal}, cost={cost}')
        except Exception as e:
            print(f'Error querying quotation: {e}')
        
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
