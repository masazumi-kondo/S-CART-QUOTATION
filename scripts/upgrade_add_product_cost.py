
"""
products テーブルに cost カラム (REAL DEFAULT 0) を追加する簡易スクリプト。

使い方:
  python scripts/upgrade_add_product_cost.py              # 開発用 DB に対して
  python scripts/upgrade_add_product_cost.py path/to.db   # 任意の DB に対して

- すでに cost カラムがある場合は何もしません。
"""
import os
import sqlite3
import sys

def find_db_path():
    """
    引数なしの場合、プロジェクトルート基準で estimates.db, app/estimates.db の順に探す。
    見つかったものを返す。なければ None。
    """
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'estimates.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'estimates.db'),
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if os.path.isfile(path):
            return path
    return None

def add_cost_column_if_needed(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [row[1] for row in cur.fetchall()]
        if "cost" in cols:
            print(f"[OK] products.cost column already exists in {db_path}. nothing to do.")
            conn.close()
            return
        print(f"[INFO] adding products.cost column to {db_path} ...")
        cur.execute("ALTER TABLE products ADD COLUMN cost REAL DEFAULT 0")
        conn.commit()
        conn.close()
        print("[DONE] column added.")
    except sqlite3.Error as e:
        print(f"[ERROR] SQLite error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = find_db_path()
        if not db_path:
            print("[ERROR] DB file not found. (estimates.db or app/estimates.db)", file=sys.stderr)
            sys.exit(1)
    if not os.path.isfile(db_path):
        print(f"[ERROR] DB file not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    add_cost_column_if_needed(db_path)

if __name__ == "__main__":
    main()
