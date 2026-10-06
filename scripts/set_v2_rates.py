"""V2 時間単価を DB の設定行へ反映（既存DB用）。既定: 原価 6,820 / 販売 12,000 円/h。"""
import os
import sqlite3
import sys

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.environ.get("SCART_DB_PATH") or os.path.join(base, "estimates.db")
cost = float(sys.argv[1]) if len(sys.argv) > 1 else 6820
sell = float(sys.argv[2]) if len(sys.argv) > 2 else 12000

conn = sqlite3.connect(db_path)
cur = conn.execute("UPDATE v2_calculation_settings SET cost_hourly_rate=?, sell_hourly_rate=? WHERE id=1", (cost, sell))
conn.commit()
print(f"updated rows={cur.rowcount}: cost={cost} sell={sell} ({db_path})")
conn.close()
