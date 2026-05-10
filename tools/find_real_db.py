import os
import sqlite3

ROOT = os.path.abspath(".")
CANDIDATES = []

def is_sqlite_file(path: str) -> bool:
    # sqlite header: "SQLite format 3\0"
    try:
        with open(path, "rb") as f:
            return f.read(16).startswith(b"SQLite format 3\x00")
    except Exception:
        return False

def has_table(path: str, table: str) -> bool:
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
        row = cur.fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False

def count_rows(path: str, table: str) -> int:
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        n = int(cur.fetchone()[0])
        conn.close()
        return n
    except Exception:
        return -1

def main():
    # search typical places first
    likely = [
        os.path.join(ROOT, "quotation.db"),
        os.path.join(ROOT, "estimates.db"),
        os.path.join(ROOT, "app", "db", "quotation.db"),
        os.path.join(ROOT, "app", "db", "estimates.db"),
    ]
    checked = set()

    def check(p):
        p = os.path.abspath(p)
        if p in checked or not os.path.exists(p):
            return
        checked.add(p)
        if not is_sqlite_file(p):
            return
        if has_table(p, "quotations"):
            rows = count_rows(p, "quotations")
            print(f"[FOUND] quotations table in: {p} (rows={rows})")

    for p in likely:
        check(p)

    # full scan (limited to .db/.sqlite/.sqlite3)
    exts = (".db", ".sqlite", ".sqlite3")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip venv/node_modules if present
        lower = dirpath.lower()
        if "\\.venv" in lower or "\\venv" in lower or "\\node_modules" in lower:
            continue
        for fn in filenames:
            if fn.lower().endswith(exts):
                check(os.path.join(dirpath, fn))

    print("[DONE] scan complete")

if __name__ == "__main__":
    main()
