import sqlite3
import os
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join("app", "db", "quotation.db")
DB_PATH = os.path.abspath(DB_PATH)
ALTERS = [
    "ALTER TABLE quotations ADD COLUMN calc_mode TEXT;",
    "ALTER TABLE quotations ADD COLUMN avg_entry_dirs REAL;",
    "ALTER TABLE quotations ADD COLUMN station_auto INTEGER;",
    "ALTER TABLE quotations ADD COLUMN station_manual INTEGER;",
    "ALTER TABLE quotations ADD COLUMN station_relay INTEGER;",
    "ALTER TABLE quotations ADD COLUMN station_charge INTEGER;",
    "ALTER TABLE quotations ADD COLUMN wait_position_count INTEGER;",
    "ALTER TABLE quotations ADD COLUMN has_swap_operation INTEGER;",
    "ALTER TABLE quotations ADD COLUMN has_plc_handshake INTEGER;",
    "ALTER TABLE quotations ADD COLUMN has_ev_integration INTEGER;",
    "ALTER TABLE quotations ADD COLUMN difficulty_design TEXT;",
    "ALTER TABLE quotations ADD COLUMN difficulty_setup TEXT;",
]


def main():
    print("[MIGRATE] DB_PATH =", DB_PATH)
    if not os.path.exists(DB_PATH):
        print("[MIGRATE] DB not found")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for sql in ALTERS:
        try:
            cur.execute(sql)
            print(f"OK: {sql.strip()}")
        except Exception as e:
            print(f"SKIP/ERR: {sql.strip()} -> {e}")
    conn.commit()
    # legacy埋め
    try:
        cur.execute("UPDATE quotations SET calc_mode = 'legacy' WHERE calc_mode IS NULL OR TRIM(calc_mode) = '';")
        print("OK: legacy calc_mode update")
    except Exception as e:
        print(f"ERR: legacy calc_mode update -> {e}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
