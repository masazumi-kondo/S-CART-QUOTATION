#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
現行DB (app/db/scart.db) の業務データをクリア
users テーブルのみを保持する安全スクリプト

使用方法:
  DRY RUN（削除実行なし）:
    python scripts/clear_current_db_keep_users.py
  
  本実行（データ削除）:
    python scripts/clear_current_db_keep_users.py --execute
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import sys
import os

# UTF-8出力設定
if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = Path("estimates.db")
BACKUP_DIR = Path("app/db/backups")


def create_backup():
    """DBファイルのバックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"scart_backup_before_clear_{timestamp}.db"
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"[OK] バックアップ作成: {backup_path}")
    return backup_path


def get_all_tables(conn):
    """DB内の全テーブル一覧を取得"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def get_table_counts(conn, tables):
    """指定されたテーブル一覧の件数を取得"""
    cursor = conn.cursor()
    counts = {}
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            counts[table] = count
        except Exception as e:
            print(f"⚠️  {table}: 件数取得失敗 - {e}")
            counts[table] = -1
    
    return counts


def clear_table_data(conn, tables_to_clear):
    """指定されたテーブルのデータを削除"""
    cursor = conn.cursor()
    
    # 外部キー制約を一時的に無効化
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    deleted_count = 0
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            deleted_count += cursor.rowcount
            print(f"  [OK] {table}: {cursor.rowcount} 件削除")
        except Exception as e:
            print(f"  ✗ {table}: 削除失敗 - {e}")
    
    # 外部キー制約を再度有効化
    cursor.execute("PRAGMA foreign_keys = ON")
    
    return deleted_count


def reset_sequences(conn, tables_to_clear):
    """sqlite_sequence をリセット"""
    cursor = conn.cursor()
    
    # sqlite_sequence テーブルが存在するか確認
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='table' AND name='sqlite_sequence'
    """)
    
    if cursor.fetchone()[0] == 0:
        print("  (sqlite_sequence テーブル: なし)")
        return
    
    # users以外のsequenceをリセット
    tables_set = set(tables_to_clear)
    
    cursor.execute("SELECT name FROM sqlite_sequence")
    seq_tables = [row[0] for row in cursor.fetchall()]
    
    for seq_table in seq_tables:
        if seq_table not in tables_set:
            continue
        try:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name=?", (seq_table,))
            print(f"  [OK] sqlite_sequence: {seq_table} リセット")
        except Exception as e:
            print(f"  ⚠️  sqlite_sequence: {seq_table} リセット失敗 - {e}")


def initialize_db_if_needed():
    """DBが空の場合、Flask を通じて初期化"""
    if DB_PATH.stat().st_size == 0:
        print("[WARN] DBが未初期化です。Flask モデルから初期化します...\n")
        try:
            # スクリプトの親ディレクトリをパスに追加
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))
            
            from app import create_app, db
            app = create_app()
            with app.app_context():
                db.create_all()
            print("[OK] DB初期化完了\n")
        except Exception as e:
            print(f"❌ DB初期化失敗: {e}\n")
            import traceback
            traceback.print_exc()
            return False
    return True


def main():
    """メイン処理"""
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description="現行DB の業務データをクリア（users のみ保持）"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際にデータを削除する（省略時は DRY RUN）"
    )
    args = parser.parse_args()
    
    print("=" * 100)
    print("現行DB クリアスクリプト (users保持版)")
    print("=" * 100)
    
    # DBファイル存在確認
    if not DB_PATH.exists():
        print(f"❌ DBファイルが見つかりません: {DB_PATH}")
        sys.exit(1)
    
    print(f"\nDB: {DB_PATH}")
    print(f"モード: {'本実行' if args.execute else 'DRY RUN'}")
    print()
    
    # DB初期化（必要な場合）
    if not initialize_db_if_needed():
        print("❌ DBの初期化に失敗しました")
        sys.exit(1)
    
    # DB接続
    try:
        conn = sqlite3.connect(str(DB_PATH))
    except Exception as e:
        print(f"❌ DB接続失敗: {e}")
        sys.exit(1)
    
    # テーブル一覧取得
    all_tables = get_all_tables(conn)
    preserve_tables = {"users"}  # 保持するテーブル
    tables_to_clear = [t for t in all_tables if t not in preserve_tables]
    
    print("=" * 100)
    print("1. テーブル分類")
    print("=" * 100)
    
    print(f"\n【保持テーブル】")
    for t in preserve_tables:
        if t in all_tables:
            print(f"  [+] {t}")
    
    print(f"\n【削除対象テーブル】({len(tables_to_clear)}個)")
    for t in sorted(tables_to_clear):
        print(f"  - {t}")
    
    # 削除前の件数取得
    print("\n" + "=" * 100)
    print("2. 削除前の件数確認")
    print("=" * 100)
    
    before_counts = get_table_counts(conn, all_tables)
    
    users_before = before_counts.get("users", 0)
    print(f"\n【保持テーブル件数】")
    print(f"  users: {users_before} 件")
    
    print(f"\n【削除対象テーブル件数】")
    total_to_delete = 0
    for table in sorted(tables_to_clear):
        count = before_counts.get(table, 0)
        if count > 0:
            print(f"  [+] {table:30s}: {count:6d} 件")
            total_to_delete += count
    print(f"  {'合計':30s}: {total_to_delete:6d} 件")
    
    # DRY RUN 時は終了
    if not args.execute:
        print("\n" + "=" * 100)
        print("🔍 DRY RUN: データ削除は実行していません")
        print("=" * 100)
        print("\n本実行するには以下を実行してください:")
        print("  python scripts/clear_current_db_keep_users.py --execute\n")
        conn.close()
        return
    
    # 本実行
    print("\n" + "=" * 100)
    print("3. バックアップ作成")
    print("=" * 100)
    backup_path = create_backup()
    
    print("\n" + "=" * 100)
    print("4. データ削除実行")
    print("=" * 100)
    
    print("\n【テーブルデータ削除】")
    deleted_rows = clear_table_data(conn, tables_to_clear)
    
    print("\n【Sequence リセット】")
    reset_sequences(conn, tables_to_clear)
    
    # コミット
    try:
        conn.commit()
        print("\n✓ コミット完了")
    except Exception as e:
        print(f"❌ コミット失敗: {e}")
        conn.close()
        sys.exit(1)
    
    # 削除後の件数確認
    print("\n" + "=" * 100)
    print("5. 削除後の件数確認")
    print("=" * 100)
    
    after_counts = get_table_counts(conn, all_tables)
    
    users_after = after_counts.get("users", 0)
    
    print(f"\n【保持テーブル件数】")
    print(f"  users: {users_after} 件")
    
    # Users 件数の検証
    if users_before != users_after:
        print(f"\n❌ エラー: users の件数が変化しました")
        print(f"   削除前: {users_before}")
        print(f"   削除後: {users_after}")
        print(f"\n⚠️  バックアップから復旧してください:")
        print(f"   {backup_path}")
        conn.close()
        sys.exit(1)
    else:
        print(f"  [OK] users 件数維持確認: {users_before} -> {users_after} [OK]")
    
    print(f"\n【削除対象テーブル件数（削除後）】")
    total_remaining = 0
    for table in sorted(tables_to_clear):
        count = after_counts.get(table, 0)
        if count > 0:
            print(f"  ⚠️  {table:30s}: {count:6d} 件（削除失敗）")
            total_remaining += count
        else:
            print(f"  ✓ {table:30s}: 0 件")
    
    if total_remaining > 0:
        print(f"\n❌ 警告: {total_remaining} 件のデータが残存しています")
    else:
        print(f"  [OK] 全テーブル削除確認")
    
    conn.close()
    
    # 完了レポート
    print("\n" + "=" * 100)
    print("✅ 完了")
    print("=" * 100)
    print(f"\nバックアップ: {backup_path}")
    print(f"削除データ: {deleted_rows} 件")
    print(f"Users 保持: {users_after} 件")
    print("\n次のステップ:")
    print("  1. アプリを起動してログインできることを確認")
    print("  2. /quotations が空になっていることを確認")
    print("  3. /customers が空になっていることを確認")
    print("  4. /products が空になっていることを確認\n")


if __name__ == "__main__":
    main()
