#!/usr/bin/env python
import sqlite3

db_path = 'estimates.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if cost column exists
cursor.execute("PRAGMA table_info(quotation_details)")
columns = cursor.fetchall()
col_names = [col[1] for col in columns]

if 'cost' not in col_names:
    print("Adding cost column to quotation_details...")
    cursor.execute("ALTER TABLE quotation_details ADD COLUMN cost REAL DEFAULT 0")
    conn.commit()
    print("✓ cost column added")
else:
    print("✓ cost column already exists")

# Verify
cursor.execute("PRAGMA table_info(quotation_details)")
columns = cursor.fetchall()
print("\nCurrent columns:")
for col in columns:
    print(f"  - {col[1]}")

conn.close()
