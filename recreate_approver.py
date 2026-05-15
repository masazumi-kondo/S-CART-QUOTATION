#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Recreate approver user"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Delete existing approver
        existing = User.query.filter_by(login_id="approver").first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print("Deleted existing approver user")
        
        # Create new approver
        approver = User(
            login_id="approver",
            password_hash=generate_password_hash("approver123"),
            display_name="承認者",
            email="approver@example.com",
            role="approver",
            is_active=True,
            receive_notifications=True
        )
        db.session.add(approver)
        db.session.commit()
        print(f"Created new approver user: id={approver.id}, role={approver.role}")
