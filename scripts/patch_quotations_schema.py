#!/usr/bin/env python
"""スキーマパッチ：quotations テーブルに不足カラムを追加"""

import os
import sys

# プロジェクトルートをパスに追加
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import create_app, db
from sqlalchemy import text

COLUMNS = {
    "discount_amount": "INTEGER DEFAULT 0",
    "estimator_name": "VARCHAR(100)",
    "calc_mode": "VARCHAR",
    "avg_entry_dirs": "FLOAT",
    "station_auto": "INTEGER",
    "station_manual": "INTEGER",
    "station_relay": "INTEGER",
    "station_charge": "INTEGER",
    "wait_position_count": "INTEGER",
    "has_swap_operation": "BOOLEAN",
    "has_plc_handshake": "BOOLEAN",
    "has_ev_integration": "BOOLEAN",
    "difficulty_design": "VARCHAR",
    "difficulty_setup": "VARCHAR",
}

app = create_app()

with app.app_context():
    existing = db.session.execute(text("PRAGMA table_info(quotations)")).fetchall()
    existing_names = {row[1] for row in existing}

    print(f"[INFO] existing columns: {existing_names}")

    for name, ddl in COLUMNS.items():
        if name not in existing_names:
            sql = f"ALTER TABLE quotations ADD COLUMN {name} {ddl}"
            print(f"[INFO] Adding column: {sql}")
            try:
                db.session.execute(text(sql))
            except Exception as e:
                print(f"[WARN] Failed to add {name}: {e}")

    db.session.commit()
    print("[OK] quotations schema patch done.")
