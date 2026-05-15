#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Direct approver role check"""
import sys
sys.path.insert(0, '.')
from app import create_app, db
from app.models.user import User

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        u = User.query.filter_by(login_id='approver').first()
        if u:
            print(f"Approver user found:")
            print(f"  id={u.id}")
            print(f"  login_id={u.login_id}")
            print(f"  role={repr(u.role)}")
            print(f"  is_active={u.is_active}")
            
            # Check role matching
            required_roles = ('admin', 'approver')
            print(f"\nRole checks:")
            print(f"  u.role in required_roles: {u.role in required_roles}")
            print(f"  u.role == 'approver': {u.role == 'approver'}")
            print(f"  u.role == 'admin': {u.role == 'admin'}")
            
            # Check what happens when we access role
            if hasattr(u, 'role'):
                print(f"\n  role is attribute: True")
                print(f"  role value: {u.role}")
                print(f"  role type: {type(u.role)}")
            else:
                print(f"\n  role is attribute: False")
        else:
            print("approver user not found")
