#!/usr/bin/env python
"""マイグレーション：discount_amount カラムを quotations テーブルに追加"""

from app import create_app, db
from sqlalchemy import text

def main():
    app = create_app()
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        cols = [col['name'] for col in inspector.get_columns('quotations')]
        
        if 'discount_amount' in cols:
            print('[OK] discount_amount column already exists')
        else:
            print('[INFO] Creating discount_amount column...')
            try:
                db.session.execute(text('ALTER TABLE quotations ADD COLUMN discount_amount INTEGER DEFAULT 0'))
                db.session.commit()
                print('[OK] discount_amount column created')
            except Exception as e:
                print(f'[ERROR] {e}')
                db.session.rollback()

if __name__ == '__main__':
    main()
