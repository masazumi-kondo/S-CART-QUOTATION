#!/usr/bin/env python
"""
Restore project_name from old DB to current DB

Usage:
  DRY RUN:  python scripts/restore_project_names_from_old_db.py
  Execute:  python scripts/restore_project_names_from_old_db.py --execute
"""

import sqlite3
from pathlib import Path
import sys
import shutil
from datetime import datetime

OLD_DB_PATH = Path("estimates - old.db")
CURRENT_DB_PATH = Path("estimates.db")
BACKUP_DIR = Path("backups")

def connect_db(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def main():
    # Check if execute flag is passed
    execute = "--execute" in sys.argv
    
    if not OLD_DB_PATH.exists():
        print(f"ERROR: {OLD_DB_PATH} not found")
        sys.exit(1)
    
    if not CURRENT_DB_PATH.exists():
        print(f"ERROR: {CURRENT_DB_PATH} not found")
        sys.exit(1)
    
    print("=" * 80)
    print("Restore project_name from old DB to current DB")
    print("=" * 80)
    
    # Connect to both DBs
    old_conn = connect_db(OLD_DB_PATH)
    cur_conn = connect_db(CURRENT_DB_PATH)
    old_cur = old_conn.cursor()
    cur_cur = cur_conn.cursor()
    
    # Get old DB data: id -> project_name
    print("\nFetching old DB data...")
    old_data = {}
    try:
        rows = old_cur.execute("SELECT id, project_name FROM quotations ORDER BY id").fetchall()
        for row in rows:
            old_data[row['id']] = row['project_name']
        print(f"  Found {len(old_data)} records in old DB")
    except Exception as e:
        print(f"ERROR reading old DB: {e}")
        old_conn.close()
        cur_conn.close()
        sys.exit(1)
    
    # Check current DB for empty project_name
    print("\nChecking current DB for empty project_name...")
    try:
        empty_rows = cur_cur.execute(
            "SELECT id, project_name FROM quotations WHERE project_name IS NULL OR project_name = '' ORDER BY id"
        ).fetchall()
        print(f"  Found {len(empty_rows)} records with empty project_name")
    except Exception as e:
        print(f"ERROR reading current DB: {e}")
        old_conn.close()
        cur_conn.close()
        sys.exit(1)
    
    # Prepare updates
    print("\n" + "=" * 80)
    print("Update Candidates:")
    print("=" * 80)
    updates = []
    skipped = []
    
    for row in empty_rows:
        cur_id = row['id']
        if cur_id in old_data:
            old_project_name = old_data[cur_id]
            if old_project_name and old_project_name.strip():
                updates.append((old_project_name, cur_id))
                print(f"  ID={cur_id}: will update to '{old_project_name}'")
            else:
                skipped.append((cur_id, "Old DB project_name is empty"))
                print(f"  ID={cur_id}: SKIP - old DB project_name is empty")
        else:
            skipped.append((cur_id, "No matching ID in old DB"))
            print(f"  ID={cur_id}: SKIP - no matching ID in old DB")
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print("=" * 80)
    print(f"  Ready to update: {len(updates)} records")
    print(f"  Will skip: {len(skipped)} records")
    
    if skipped:
        print("\n  Skipped reasons:")
        for cur_id, reason in skipped:
            print(f"    ID={cur_id}: {reason}")
    
    if not updates:
        print("\nNo updates needed")
        old_conn.close()
        cur_conn.close()
        return
    
    if not execute:
        print("\n" + "=" * 80)
        print("DRY RUN - No changes made")
        print("=" * 80)
        print("To execute, run: python scripts/restore_project_names_from_old_db.py --execute")
        old_conn.close()
        cur_conn.close()
        return
    
    # Create backup
    print("\nCreating backup...")
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_file = BACKUP_DIR / f"estimates.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy(CURRENT_DB_PATH, backup_file)
        print(f"  Backup created: {backup_file}")
    except Exception as e:
        print(f"ERROR creating backup: {e}")
        old_conn.close()
        cur_conn.close()
        sys.exit(1)
    
    # Perform updates
    print("\nExecuting updates...")
    try:
        for project_name, cur_id in updates:
            cur_cur.execute(
                "UPDATE quotations SET project_name = ? WHERE id = ?",
                (project_name, cur_id)
            )
            print(f"  Updated ID={cur_id}: '{project_name}'")
        
        cur_conn.commit()
        print(f"\nSuccessfully updated {len(updates)} records")
    except Exception as e:
        print(f"ERROR during update: {e}")
        cur_conn.rollback()
        old_conn.close()
        cur_conn.close()
        sys.exit(1)
    
    # Verify
    print("\n" + "=" * 80)
    print("Verification:")
    print("=" * 80)
    empty_now = cur_cur.execute(
        "SELECT COUNT(*) FROM quotations WHERE project_name IS NULL OR project_name = ''"
    ).fetchone()[0]
    print(f"  Remaining empty project_name: {empty_now}")
    
    filled_now = cur_cur.execute(
        "SELECT COUNT(*) FROM quotations WHERE project_name IS NOT NULL AND project_name != ''"
    ).fetchone()[0]
    print(f"  Total filled project_name: {filled_now}")
    
    old_conn.close()
    cur_conn.close()
    
    print("\n" + "=" * 80)
    print("Restore completed successfully")
    print("=" * 80)

if __name__ == "__main__":
    main()
