#!/usr/bin/env python
import sqlite3

db_path = 'estimates.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

rows = cur.execute('''
    SELECT id, quotation_no, discount_amount 
    FROM quotations 
    ORDER BY id 
    LIMIT 10
''').fetchall()

print("Quotations discount check:")
print(f"{'ID':<4} {'No':<10} {'Discount Amount':<20}")
print("-" * 40)
for row in rows:
    q_id, q_no, discount = row
    discount_val = discount or 0
    print(f"{q_id:<4} {q_no:<10} {str(discount_val):<20}")

# Find quotations with discount = 0 and > 0
zero_count = cur.execute('SELECT COUNT(*) FROM quotations WHERE discount_amount = 0 OR discount_amount IS NULL').fetchone()[0]
nonzero_count = cur.execute('SELECT COUNT(*) FROM quotations WHERE discount_amount > 0').fetchone()[0]

print(f"\nSummary:")
print(f"  With no discount (0/NULL): {zero_count}")
print(f"  With discount (> 0): {nonzero_count}")

conn.close()
