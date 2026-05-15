#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check approver user details"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.user import User

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        users = db.session.query(User).all()
        for user in users:
            print(f"User ID={user.id}, login_id={user.login_id}, role={user.role}, is_active={user.is_active}")
            if user.login_id == "approver":
                print(f"  Approver details: id={user.id}, role_value='{user.role}', role type={type(user.role)}")
