#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check exact approver role value"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.user import User
import sqlite3

if __name__ == "__main__":
    # Check via SQLAlchemy
    app = create_app()
    with app.app_context():
        approver = db.session.query(User).filter_by(login_id="approver").first()
        if approver:
            print(f"SQLAlchemy: approver.role = '{approver.role}' (type={type(approver.role).__name__})")
            print(f"SQLAlchemy: approver.id = {approver.id}")
            print(f"SQLAlchemy: repr(approver.role) = {repr(approver.role)}")
            print(f"SQLAlchemy: ord values: {[ord(c) for c in approver.role]}")
        else:
            print("approver user not found")
    
    # Check via raw SQL
    import os
    db_path = os.path.join(os.path.dirname(__file__), "estimates.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, login_id, role, hex(role) FROM users WHERE login_id = 'approver'")
    row = cursor.fetchone()
    if row:
        print(f"\nRaw SQL: id={row[0]}, login_id={row[1]}, role='{row[2]}', hex={row[3]}")
    conn.close()
