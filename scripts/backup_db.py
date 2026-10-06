"""SQLite オンラインバックアップ（稼働中でも安全）。日次でタスクスケジューラ実行を想定。

使い方: python scripts/backup_db.py [バックアップ先ディレクトリ] [保持日数]
DBは SCART_DB_PATH（未設定なら リポジトリ直下 estimates.db）。
"""
import os
import sqlite3
import sys
import time
from datetime import datetime

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.environ.get("SCART_DB_PATH") or os.path.join(base, "estimates.db")
dest_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, "backups")
keep_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

os.makedirs(dest_dir, exist_ok=True)
dest = os.path.join(dest_dir, f"estimates_{datetime.now():%Y%m%d_%H%M%S}.db")

src = sqlite3.connect(db_path)
dst = sqlite3.connect(dest)
with dst:
    src.backup(dst)
src.close()
dst.close()
print(f"backup ok: {dest}")

cutoff = time.time() - keep_days * 86400
for f in os.listdir(dest_dir):
    fp = os.path.join(dest_dir, f)
    if f.startswith("estimates_") and f.endswith(".db") and os.path.getmtime(fp) < cutoff:
        os.remove(fp)
        print(f"removed old: {f}")
