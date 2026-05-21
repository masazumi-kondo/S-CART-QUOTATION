#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
旧DB (estimates - old.db) から現DB (estimates.db) へのデータマイグレーション

実行方法：
  DRY RUN: python scripts/migrate_from_old_db_v2.py
  本実行:  python scripts/migrate_from_old_db_v2.py --execute
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import argparse
import sys

# 設定
OLD_DB_PATH = Path("estimates - old.db")
CURRENT_DB_PATH = Path("estimates.db")

def connect_db(db_path):
    """DB接続"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def migrate_products(old_conn, current_conn, execute=False):
    """商品マイグレーション"""
    print("\n=== Phase 1: 商品マイグレーション ===")
    
    old_cursor = old_conn.cursor()
    current_cursor = current_conn.cursor()
    
    # 旧DB から取得
    old_cursor.execute("""
        SELECT id, name, unit_price, note, cost
        FROM products
        ORDER BY id
    """)
    products = old_cursor.fetchall()
    print(f"\n旧DB: {len(products)} 件の商品")
    
    if not products:
        print("マイグレーション対象なし")
        return
    
    # 現DB へ INSERT
    insert_count = 0
    for prod in products:
        try:
            current_cursor.execute("""
                INSERT INTO products (id, name, unit_price, note, cost, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                prod['id'],
                prod['name'],
                prod['unit_price'],
                prod['note'] if prod['note'] else '',
                prod['cost'] if prod['cost'] else 0,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"  [INSERT] ID={prod['id']}: {prod['name']}")
            insert_count += 1
        except Exception as e:
            print(f"  [ERROR] ID={prod['id']}: {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT完了")
    else:
        print(f"\n[DRY RUN] {insert_count} 件 INSERT予定（実行なし）")

def extract_customers_from_quotations(old_conn):
    """quotations から company_name のリストを抽出"""
    cursor = old_conn.cursor()
    cursor.execute("""
        SELECT DISTINCT company_name 
        FROM quotations
        WHERE company_name IS NOT NULL
        ORDER BY company_name
    """)
    
    companies = [row[0] for row in cursor.fetchall()]
    return companies

def migrate_customers(old_conn, current_conn, execute=False):
    """顧客マイグレーション (quotations から自動抽出)"""
    print("\n=== Phase 2: 顧客マイグレーション ===")
    
    current_cursor = current_conn.cursor()
    
    # 旧DB から company_name を抽出
    companies = extract_customers_from_quotations(old_conn)
    print(f"\n旧DB quotations から抽出: {len(companies)} 件の会社")
    
    for i, company_name in enumerate(companies, 1):
        print(f"  {i}. {company_name}")
    
    # 現DB へ INSERT
    insert_count = 0
    for idx, company_name in enumerate(companies, 1):
        try:
            # customer_code を生成
            customer_code = f"CUST{idx:04d}"
            
            current_cursor.execute("""
                INSERT INTO customers (name, customer_code, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                company_name,
                customer_code,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            print(f"  [INSERT] {company_name}")
            insert_count += 1
        except Exception as e:
            print(f"  [ERROR] {company_name}: {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT完了")
    else:
        print(f"\n[DRY RUN] {insert_count} 件 INSERT予定（実行なし）")
    
    return companies

def get_customer_id_map(current_conn, companies):
    """company_name → customer_id マッピング"""
    cursor = current_conn.cursor()
    mapping = {}
    for company_name in companies:
        cursor.execute("SELECT id FROM customers WHERE name = ?", (company_name,))
        row = cursor.fetchone()
        if row:
            mapping[company_name] = row[0]
    return mapping

def migrate_quotations(old_conn, current_conn, customer_id_map, execute=False):
    """見積書マイグレーション"""
    print("\n=== Phase 3: 見積書マイグレーション ===")
    
    old_cursor = old_conn.cursor()
    current_cursor = current_conn.cursor()
    
    # 旧DB から取得
    old_cursor.execute("""
        SELECT id, company_name, discount_rate, created_at
        FROM quotations
        ORDER BY id
    """)
    quotations = old_cursor.fetchall()
    print(f"\n旧DB: {len(quotations)} 件の見積書")
    
    if not quotations:
        print("マイグレーション対象なし")
        return {}
    
    # ID マップを作成（旧ID → 新ID）
    old_to_new_quotation_id = {}
    insert_count = 0
    
    for quot in quotations:
        try:
            customer_id = customer_id_map.get(quot['company_name'])
            if not customer_id:
                print(f"  [SKIP] ID={quot['id']}: 顧客 '{quot['company_name']}' が見つかりません")
                continue
            
            # 割引率 → 割引額に変換（仮計算用に unit_price 合計を取得）
            detail_cursor = old_conn.cursor()
            detail_cursor.execute("""
                SELECT SUM(price * quantity) as total_price
                FROM quotation_details
                WHERE quotation_id = ?
            """, (quot['id'],))
            detail_row = detail_cursor.fetchone()
            total_price = detail_row[0] if detail_row and detail_row[0] else 0
            
            discount_amount = 0
            if quot['discount_rate'] and total_price:
                discount_amount = int(total_price * quot['discount_rate'] / 100)
            
            # quotation_no を生成（ID を使用）
            quotation_no = f"Q{quot['id']:05d}"
            
            current_cursor.execute("""
                INSERT INTO quotations (quotation_no, customer_id, discount_amount, discount_rate, 
                                       created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                quotation_no,
                customer_id,
                discount_amount,
                quot['discount_rate'] if quot['discount_rate'] else 0,
                quot['created_at'],
                datetime.now().isoformat()
            ))
            
            new_id = current_cursor.lastrowid
            old_to_new_quotation_id[quot['id']] = new_id
            
            print(f"  [INSERT] ID={quot['id']}→{new_id}: NO.{quotation_no}")
            insert_count += 1
        except Exception as e:
            print(f"  [ERROR] ID={quot['id']}: {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT完了")
    else:
        print(f"\n[DRY RUN] {insert_count} 件 INSERT予定（実行なし）")
    
    return old_to_new_quotation_id

def migrate_quotation_details(old_conn, current_conn, quotation_id_map, execute=False):
    """見積詳細マイグレーション"""
    print("\n=== Phase 4: 見積詳細マイグレーション ===")
    
    old_cursor = old_conn.cursor()
    current_cursor = current_conn.cursor()
    
    # 旧DB から取得
    old_cursor.execute("""
        SELECT id, quotation_id, product_id, label, quantity, price, profit_rate, subtotal, description
        FROM quotation_details
        ORDER BY id
    """)
    details = old_cursor.fetchall()
    print(f"\n旧DB: {len(details)} 件の見積詳細")
    
    if not details:
        print("マイグレーション対象なし")
        return
    
    insert_count = 0
    skip_count = 0
    
    for detail in details:
        try:
            new_quotation_id = quotation_id_map.get(detail['quotation_id'])
            if not new_quotation_id:
                skip_count += 1
                continue
            
            # product_id が NULL の場合もある
            product_id = detail['product_id'] if detail['product_id'] else None
            
            current_cursor.execute("""
                INSERT INTO quotation_details (quotation_id, product_id, label, quantity, unit_price, 
                                              subtotal, profit_rate, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_quotation_id,
                product_id,
                detail['label'] if detail['label'] else '',
                detail['quantity'],
                detail['price'],
                detail['subtotal'],
                detail['profit_rate'] if detail['profit_rate'] else 0,
                detail['description'] if detail['description'] else '',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            insert_count += 1
        except Exception as e:
            print(f"  [ERROR] ID={detail['id']}: {str(e)}")
    
    if execute:
        current_conn.commit()
        print(f"\n[OK] {insert_count} 件 INSERT完了, {skip_count} 件 スキップ")
    else:
        print(f"\n[DRY RUN] {insert_count} 件 INSERT予定, {skip_count} 件 スキップ（実行なし）")

def verify_migration(old_conn, current_conn):
    """マイグレーション検証"""
    print("\n=== Phase 5: 検証 ===")
    
    old_cursor = old_conn.cursor()
    current_cursor = current_conn.cursor()
    
    # 旧DB 件数
    old_cursor.execute("SELECT COUNT(*) FROM products")
    old_products = old_cursor.fetchone()[0]
    
    old_cursor.execute("SELECT COUNT(*) FROM quotations")
    old_quotations = old_cursor.fetchone()[0]
    
    old_cursor.execute("SELECT COUNT(*) FROM quotation_details")
    old_details = old_cursor.fetchone()[0]
    
    # 現DB 件数
    current_cursor.execute("SELECT COUNT(*) FROM products")
    new_products = current_cursor.fetchone()[0]
    
    current_cursor.execute("SELECT COUNT(*) FROM customers")
    new_customers = current_cursor.fetchone()[0]
    
    current_cursor.execute("SELECT COUNT(*) FROM quotations")
    new_quotations = current_cursor.fetchone()[0]
    
    current_cursor.execute("SELECT COUNT(*) FROM quotation_details")
    new_details = current_cursor.fetchone()[0]
    
    print("\n旧DB 件数:")
    print(f"  products:           {old_products} 件")
    print(f"  quotations:         {old_quotations} 件")
    print(f"  quotation_details:  {old_details} 件")
    
    print("\n現DB 件数:")
    print(f"  products:           {new_products} 件")
    print(f"  customers:          {new_customers} 件")
    print(f"  quotations:         {new_quotations} 件")
    print(f"  quotation_details:  {new_details} 件")
    
    print("\n検証結果:")
    if new_products == old_products:
        print(f"  [OK] products:     {new_products} 件")
    else:
        print(f"  [NG] products:     {old_products} -> {new_products} 件")
    
    if new_quotations == old_quotations:
        print(f"  [OK] quotations:   {new_quotations} 件")
    else:
        print(f"  [WARN] quotations: {old_quotations} -> {new_quotations} 件")
    
    if new_details == old_details:
        print(f"  [OK] details:      {new_details} 件")
    else:
        print(f"  [WARN] details:    {old_details} -> {new_details} 件")

def main():
    parser = argparse.ArgumentParser(description="旧DB -> 現DB マイグレーション")
    parser.add_argument('--execute', action='store_true', help='本実行（デフォルトは DRY RUN）')
    args = parser.parse_args()
    
    # DB 存在確認
    if not OLD_DB_PATH.exists():
        print(f"ERROR: {OLD_DB_PATH} が見つかりません")
        return
    
    if not CURRENT_DB_PATH.exists():
        print(f"ERROR: {CURRENT_DB_PATH} が見つかりません")
        return
    
    # 接続
    old_conn = connect_db(OLD_DB_PATH)
    current_conn = connect_db(CURRENT_DB_PATH)
    
    print("=" * 100)
    print("旧DB -> 現DB マイグレーション")
    print("=" * 100)
    print(f"\n旧DB:  {OLD_DB_PATH}")
    print(f"現DB:  {CURRENT_DB_PATH}")
    print(f"モード: {'本実行' if args.execute else 'DRY RUN'}")
    
    try:
        # Phase 1: 商品
        migrate_products(old_conn, current_conn, args.execute)
        
        # Phase 2: 顧客
        companies = migrate_customers(old_conn, current_conn, args.execute)
        customer_id_map = get_customer_id_map(current_conn, companies)
        
        # Phase 3: 見積書
        quotation_id_map = migrate_quotations(old_conn, current_conn, customer_id_map, args.execute)
        
        # Phase 4: 見積詳細
        migrate_quotation_details(old_conn, current_conn, quotation_id_map, args.execute)
        
        # Phase 5: 検証
        verify_migration(old_conn, current_conn)
        
        if not args.execute:
            print("\n" + "=" * 100)
            print("[DRY RUN] データマイグレーションは実行していません")
            print("本実行するには以下を実行してください:")
            print("  python scripts/migrate_from_old_db_v2.py --execute")
            print("=" * 100)
        else:
            print("\n" + "=" * 100)
            print("[SUCCESS] マイグレーション完了！")
            print("=" * 100)
    
    finally:
        old_conn.close()
        current_conn.close()

if __name__ == "__main__":
    main()
