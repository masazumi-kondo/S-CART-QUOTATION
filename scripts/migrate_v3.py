#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
旧DB (estimates - old.db) から現DB (estimates.db) へのデータマイグレーション

実行方法：
  DRY RUN: python scripts/migrate_v3.py
  本実行:  python scripts/migrate_v3.py --execute
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import argparse

# 設定
OLD_DB = Path("estimates - old.db")
CURRENT_DB = Path("estimates.db")

def connect_db(db_path):
    """DB接続"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def normalize_customer_status(value):
    """顧客ステータスを正規化（小文字に統一）"""
    if not value:
        return "approved"
    value = str(value).strip().lower()
    # 承認済み判定
    if value in ["approved", "approve", "承認済み", "ok"]:
        return "approved"
    # 申請中判定
    if value in ["pending", "申請中", "承認待ち"]:
        return "pending"
    # 差戻し判定
    if value in ["rejected", "差戻し", "否認"]:
        return "rejected"
    # デフォルト: 承認済み
    return "approved"

def migrate_products(old_conn, current_conn, execute=False):
    """商品マイグレーション"""
    print("\n=== Phase 1: Products (31件) ===")
    
    old_cursor = old_conn.cursor()
    current_cursor = current_conn.cursor()
    
    old_cursor.execute("SELECT id, name, unit_price, note, cost FROM products ORDER BY id")
    products = old_cursor.fetchall()
    print(f"旧DB: {len(products)}件\n")
    
    insert_count = 0
    for prod in products:
        try:
            # products テーブルは created_at/updated_at がないので簡略化
            current_cursor.execute("""
                INSERT INTO products (id, name, unit_price, note, cost)
                VALUES (?, ?, ?, ?, ?)
            """, (
                prod['id'],
                prod['name'],
                prod['unit_price'],
                prod['note'] or '',
                prod['cost'] or 0
            ))
            print(f"  {prod['id']:3d}: {prod['name'][:40]}")
            insert_count += 1
        except Exception as e:
            print(f"  {prod['id']:3d}: ERROR - {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT")
    else:
        print(f"\n[PLAN] {insert_count} 件 INSERT予定")

def migrate_customers(old_conn, current_conn, execute=False):
    """顧客マイグレーション (quotations から抽出)"""
    print("\n=== Phase 2: Customers (company_name から自動抽出) ===")
    
    cursor = old_conn.cursor()
    cursor.execute("SELECT DISTINCT company_name FROM quotations ORDER BY company_name")
    companies = [row[0] for row in cursor.fetchall()]
    
    print(f"旧DB quotations から抽出: {len(companies)}件\n")
    for i, name in enumerate(companies, 1):
        print(f"  {i:2d}: {name}")
    
    current_cursor = current_conn.cursor()
    insert_count = 0
    
    for idx, company_name in enumerate(companies, 1):
        try:
            current_cursor.execute("""
                INSERT INTO customers (name, customer_code, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                company_name,
                f"CUST{idx:04d}",
                "approved",  # デフォルト: 承認済み（小文字）
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            insert_count += 1
        except Exception as e:
            print(f"\nERROR: {company_name} - {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT")
    else:
        print(f"\n[PLAN] {insert_count} 件 INSERT予定")
    
    return companies

def get_customer_map(current_conn, companies):
    """name -> id マップ"""
    cursor = current_conn.cursor()
    mapping = {}
    for name in companies:
        cursor.execute("SELECT id FROM customers WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            mapping[name] = row[0]
    return mapping

def migrate_quotations(old_conn, current_conn, customer_map, execute=False):
    """見積書マイグレーション"""
    print("\n=== Phase 3: Quotations (20件) ===")
    
    old_cursor = old_conn.cursor()
    old_cursor.execute("""
        SELECT id, company_name, discount_rate, created_at
        FROM quotations
        ORDER BY id
    """)
    quotations = old_cursor.fetchall()
    print(f"旧DB: {len(quotations)}件\n")
    
    old_to_new_id = {}
    current_cursor = current_conn.cursor()
    insert_count = 0
    
    for quot in quotations:
        try:
            cust_id = customer_map.get(quot['company_name'])
            if not cust_id:
                print(f"  {quot['id']:3d}: SKIP (customer not found)")
                continue
            
            # 合計額を計算
            detail_cursor = old_conn.cursor()
            detail_cursor.execute("""
                SELECT SUM(price * quantity) as total FROM quotation_details
                WHERE quotation_id = ?
            """, (quot['id'],))
            total = detail_cursor.fetchone()[0] or 0
            
            discount_amt = 0
            if quot['discount_rate'] and total:
                discount_amt = int(total * quot['discount_rate'] / 100)
            
            quotation_no = f"Q{quot['id']:05d}"
            
            current_cursor.execute("""
                INSERT INTO quotations (quotation_no, company_name, project_name, customer_id, 
                                       discount_rate, discount_amount, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                quotation_no,
                quot['company_name'],
                '',  # project_name (required but empty)
                cust_id,
                quot['discount_rate'] or 0,
                discount_amt,
                quot['created_at'],
                datetime.now().isoformat()
            ))
            
            new_id = current_cursor.lastrowid
            old_to_new_id[quot['id']] = new_id
            print(f"  {quot['id']:3d} -> {new_id:3d}: {quotation_no}")
            insert_count += 1
        except Exception as e:
            print(f"  {quot['id']:3d}: ERROR - {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT")
    else:
        print(f"\n[PLAN] {insert_count} 件 INSERT予定")
    
    return old_to_new_id

def migrate_quotation_details(old_conn, current_conn, quot_map, execute=False):
    """見積詳細マイグレーション"""
    print("\n=== Phase 4: Quotation Details (133件) ===")
    
    old_cursor = old_conn.cursor()
    old_cursor.execute("""
        SELECT id, quotation_id, product_id, label, quantity, price, profit_rate, subtotal, description
        FROM quotation_details
        ORDER BY id
    """)
    details = old_cursor.fetchall()
    print(f"旧DB: {len(details)}件\n")
    
    current_cursor = current_conn.cursor()
    insert_count = 0
    skip_count = 0
    
    for detail in details:
        try:
            new_quot_id = quot_map.get(detail['quotation_id'])
            if not new_quot_id:
                skip_count += 1
                continue
            
            current_cursor.execute("""
                INSERT INTO quotation_details (quotation_id, product_id, label, quantity, unit_price,
                                              subtotal, profit_rate, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_quot_id,
                detail['product_id'],
                detail['label'] or '',
                detail['quantity'],
                detail['price'],
                detail['subtotal'],
                detail['profit_rate'] or 0,
                detail['description'] or '',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            insert_count += 1
        except Exception as e:
            print(f"  ERROR {detail['id']}: {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT ({skip_count} skipped)")
    else:
        print(f"\n[PLAN] {insert_count} 件 INSERT予定 ({skip_count} skipped)")

def verify(old_conn, current_conn):
    """検証"""
    print("\n=== Phase 5: Verify ===\n")
    
    # 旧DB
    old_c = old_conn.cursor()
    old_c.execute("SELECT COUNT(*) FROM products")
    old_prod = old_c.fetchone()[0]
    old_c.execute("SELECT COUNT(*) FROM quotations")
    old_quot = old_c.fetchone()[0]
    old_c.execute("SELECT COUNT(*) FROM quotation_details")
    old_detail = old_c.fetchone()[0]
    
    # 現DB
    new_c = current_conn.cursor()
    new_c.execute("SELECT COUNT(*) FROM products")
    new_prod = new_c.fetchone()[0]
    new_c.execute("SELECT COUNT(*) FROM customers")
    new_cust = new_c.fetchone()[0]
    new_c.execute("SELECT COUNT(*) FROM quotations")
    new_quot = new_c.fetchone()[0]
    new_c.execute("SELECT COUNT(*) FROM quotation_details")
    new_detail = new_c.fetchone()[0]
    
    print(f"旧DB:  products={old_prod}, quotations={old_quot}, details={old_detail}")
    print(f"現DB:  products={new_prod}, customers={new_cust}, quotations={new_quot}, details={new_detail}")
    
    results = [
        ("products", new_prod, old_prod),
        ("quotations", new_quot, old_quot),
        ("details", new_detail, old_detail)
    ]
    
    print("\n検証:")
    for name, new_count, old_count in results:
        status = "[OK]" if new_count == old_count else "[WARN]"
        print(f"  {status} {name:15s}: {old_count} -> {new_count}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='本実行')
    args = parser.parse_args()
    
    if not OLD_DB.exists() or not CURRENT_DB.exists():
        print("ERROR: DB not found")
        return
    
    old_conn = connect_db(OLD_DB)
    current_conn = connect_db(CURRENT_DB)
    
    print("=" * 80)
    print("Migration: estimates - old.db -> estimates.db")
    print("=" * 80)
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")
    
    try:
        migrate_products(old_conn, current_conn, args.execute)
        companies = migrate_customers(old_conn, current_conn, args.execute)
        cust_map = get_customer_map(current_conn, companies)
        quot_map = migrate_quotations(old_conn, current_conn, cust_map, args.execute)
        migrate_quotation_details(old_conn, current_conn, quot_map, args.execute)
        verify(old_conn, current_conn)
        
        print("\n" + "=" * 80)
        if args.execute:
            print("SUCCESS! Migration completed.")
        else:
            print("DRY RUN completed. Execute with --execute to apply changes.")
            print("\n  python scripts/migrate_v3.py --execute")
        print("=" * 80)
    
    finally:
        old_conn.close()
        current_conn.close()

if __name__ == "__main__":
    main()
