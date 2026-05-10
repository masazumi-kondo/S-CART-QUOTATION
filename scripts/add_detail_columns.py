#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
quotation_details テーブルにカラムを追加するマイグレーション スクリプト
"""

import sqlite3
import sys

DB_PATH = "estimates.db"

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """カラムが存在しなければ追加"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    if column_name not in columns:
        print(f"Adding column {table_name}.{column_name}...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        print(f"  ✓ Added")
        return True
    else:
        print(f"Column {table_name}.{column_name} already exists")
        return False

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"Connecting to {DB_PATH}...")
        
        # quotation_details テーブルに必要なカラムを追加
        add_column_if_not_exists(cursor, "quotation_details", "product_id", "INTEGER")
        add_column_if_not_exists(cursor, "quotation_details", "code", "TEXT")
        add_column_if_not_exists(cursor, "quotation_details", "description", "TEXT")
        add_column_if_not_exists(cursor, "quotation_details", "price", "REAL")
        
        # 既存の unit_price を price にコピー（price がない場合）
        cursor.execute("PRAGMA table_info(quotation_details)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "unit_price" in columns and "price" in columns:
            # unit_price の値を price にコピー
            cursor.execute("UPDATE quotation_details SET price = unit_price WHERE price IS NULL OR price = 0")
            print("Copied unit_price to price for existing rows")
        
        # item_name を description にコピー（description がない場合）
        if "item_name" in columns and "description" in columns:
            cursor.execute("UPDATE quotation_details SET description = item_name WHERE description IS NULL OR description = ''")
            print("Copied item_name to description for existing rows")
        
        conn.commit()
        print("\n✓ Migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
