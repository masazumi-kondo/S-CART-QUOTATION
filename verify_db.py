import sqlite3

conn = sqlite3.connect('estimates.db')
cur = conn.cursor()

# Check both quotations 21 and 22
for qid in [21, 22]:
    cur.execute('SELECT id, project_name, company_name FROM quotations WHERE id = ?;', (qid,))
    q = cur.fetchone()
    if q:
        print(f"Quotation {qid}:")
        print(f"  Project: {q[1]}")
        print(f"  Company: {q[2]}")
        
        # Get details
        cur.execute('SELECT COUNT(*) FROM quotation_details WHERE quotation_id = ?;', (qid,))
        count = cur.fetchone()[0]
        print(f"  Details: {count} rows")
        
        cur.execute('SELECT description, price, subtotal FROM quotation_details WHERE quotation_id = ? ORDER BY rowid;', (qid,))
        rows = cur.fetchall()
        for r in rows:
            print(f"    - {r[0]}: price={r[1]}, subtotal={r[2]}")
        print()

conn.close()
