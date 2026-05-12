#!/usr/bin/env python
import sqlite3
import os

# Try both databases
for db_path in ["app/db/estimates.db", "app/db/scart.db"]:
    if not os.path.exists(db_path):
        continue
    
    print(f"\n{'=' * 80}")
    print(f"Checking: {db_path}")
    print('=' * 80)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print(f"❌ 'user' テーブルが見つかりません")
            conn.close()
            continue
        
        # Get admin users
        cursor.execute("""
            SELECT id, username, email, role, active, receive_notifications 
            FROM user 
            WHERE role='admin' 
            ORDER BY id
        """)
        rows = cursor.fetchall()
        
        if rows:
            print("✓ 管理者ユーザーが見つかりました:")
            print("=" * 80)
            for row in rows:
                notify_status = "✓ ON" if row[5] else "✗ OFF"
                active_status = "✓" if row[4] else "✗"
                print(f"  ID:{row[0]:2} | User:{row[1]:15} | Email:{row[2]:30} | Active:{active_status} | Notify:{notify_status}")
            print('=' * 80)
        else:
            print("❌ 管理者ユーザーが見つかりません")
            print("=" * 80)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        print("=" * 80)
