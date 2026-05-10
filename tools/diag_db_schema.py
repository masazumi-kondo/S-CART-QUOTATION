import os
import sys
import sqlite3

def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("app", "db", "quotation.db")
    db_path = os.path.abspath(db_path)

    print("[DIAG] DB_PATH =", db_path)
    if not os.path.exists(db_path):
        print("[DIAG] DB not found")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    print("[DIAG] tables:", tables)

    if "quotations" not in tables:
        print("[DIAG] quotations table not found")
        conn.close()
        return

    cur.execute("PRAGMA table_info(quotations);")
    cols = cur.fetchall()
    print("[DIAG] quotations columns:")
    for cid, name, ctype, notnull, dflt, pk in cols:
        print(f"  - {name} {ctype} (notnull={notnull}, dflt={dflt}, pk={pk})")

    conn.close()

if __name__ == "__main__":
    main()
