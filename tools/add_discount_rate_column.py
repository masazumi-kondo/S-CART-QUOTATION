
# tools/add_discount_rate_column.py
import os
import sys
import traceback

# ★ プロジェクトルート（SCART Quotation）を import パスに追加
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app import create_app, db
from sqlalchemy import text

def main():
    app = create_app()
    with app.app_context():
        print("DB Path:", db.engine.url)
        try:
            print("ALTER TABLE 実行中...")
            db.session.execute(
                text("ALTER TABLE quotations ADD COLUMN discount_rate REAL DEFAULT 0;")
            )
            db.session.commit()
            print("✔ OK: quotations.discount_rate カラムを追加しました。")
        except Exception as e:
            db.session.rollback()
            print("⚠ WARN: カラム追加時に例外が発生（既に追加済みの可能性あり）")
            traceback.print_exc()

if __name__ == "__main__":
    main()
