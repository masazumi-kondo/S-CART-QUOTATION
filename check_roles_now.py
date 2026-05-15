#!/usr/bin/env python3
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    users = db.session.query(User).filter(User.login_id.in_(['admin', 'approver', 'user'])).all()
    print(f"Total users found: {len(users)}")
    for u in users:
        print(f"user: {u.login_id:10} | role: {u.role:10} | is_active: {u.is_active}")
