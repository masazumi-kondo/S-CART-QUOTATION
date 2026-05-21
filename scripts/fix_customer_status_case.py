#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Customer status の大文字・小文字を統一するDB補正スクリプト

実行方法：
  DRY RUN: python scripts/fix_customer_status_case.py
  本実行:  python scripts/fix_customer_status_case.py --execute
"""

import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path("estimates.db")

def normalize_status(value):
    """顧客ステータスを正規化（小文字に統一）"""
    if not value:
        return None
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
    # 未知の値は NULL に統一
    return None

def main():
    parser = argparse.ArgumentParser(description="Customer status の大文字・小文字を統一")
    parser.add_argument('--execute', action='store_true', help='本実行（デフォルトはDRY RUN）')
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("=" * 80)
    print("Fix: Customer status case normalization")
    print("=" * 80)
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    # 修正前の統計
    cursor.execute("""
        SELECT status, COUNT(*) as cnt
        FROM customers
        GROUP BY status
        ORDER BY status
    """)
    before = cursor.fetchall()
    print("[修正前] Status 別件数:")
    for status, count in before:
        print(f"  {repr(status):20s}: {count:3d}")
    print()

    # 修正対象を抽出
    cursor.execute("SELECT id, name, status FROM customers")
    customers = cursor.fetchall()

    updates = []
    for cust_id, cust_name, old_status in customers:
        new_status = normalize_status(old_status)
        # 変更が必要かチェック
        if old_status != new_status:
            updates.append((new_status, cust_id, old_status, cust_name))

    if not updates:
        print("[OK] 修正不要です（すべてのステータスが正規化済み）\n")
    else:
        print(f"[修正対象] {len(updates)} 件\n")
        for new_status, cust_id, old_status, cust_name in updates:
            print(f"  ID {cust_id:3d}: {repr(old_status):20s} -> {repr(new_status):20s} ({cust_name})")
        print()

        if args.execute:
            for new_status, cust_id, old_status, cust_name in updates:
                cursor.execute(
                    "UPDATE customers SET status = ? WHERE id = ?",
                    (new_status, cust_id)
                )
            conn.commit()
            print(f"[OK] {len(updates)} 件を更新しました\n")
        else:
            print(f"[PLAN] {len(updates)} 件を更新予定\n")

    # 修正後の統計
    cursor.execute("""
        SELECT status, COUNT(*) as cnt
        FROM customers
        GROUP BY status
        ORDER BY status
    """)
    after = cursor.fetchall()
    print("[修正後] Status 別件数:")
    for status, count in after:
        print(f"  {repr(status):20s}: {count:3d}")
    print()

    # users, quotations は変更なしを確認
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM quotations")
    quot_count = cursor.fetchone()[0]
    print(f"[確認] users: {user_count} 件（変更なし）")
    print(f"[確認] quotations: {quot_count} 件（変更なし）")
    print()

    conn.close()

    print("=" * 80)
    if not args.execute and updates:
        print("DRY RUN completed. Execute with --execute to apply changes.")
        print("\n  python scripts/fix_customer_status_case.py --execute")
    else:
        print("Done!")
    print("=" * 80)

if __name__ == "__main__":
    main()
