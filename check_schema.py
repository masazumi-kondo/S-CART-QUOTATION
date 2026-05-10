#!/usr/bin/env python3
import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'estimates.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(quotation_details)")
columns = cursor.fetchall()
print('quotation_details columns:')
for col in columns:
    cid, name, type_, notnull, dflt_value, pk = col
    print(f'  {cid}: {name} ({type_})')

conn.close()
