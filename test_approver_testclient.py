#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test approver role with test client"""
import sys
import traceback
sys.path.insert(0, '.')
from app import create_app, db
from app.models.user import User

if __name__ == "__main__":
    app = create_app()
    
    # Create test client
    client = app.test_client()
    
    # Check approver user
    with app.app_context():
        approver = User.query.filter_by(login_id="approver").first()
        if approver:
            print(f"Approver user: id={approver.id}, role={approver.role}")
        else:
            print("approver user not found")
    
    # Test with test client
    try:
        with client:
            # Login
            response = client.post('/login', data={
                'login_id': 'approver',
                'password': 'approver123'
            }, follow_redirects=True)
            print(f"\nLogin response status: {response.status_code}")
            
            # Access /customers/pending
            response = client.get('/customers/pending')
            print(f"GET /customers/pending status: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ Approver CAN access /customers/pending via test client")
            elif response.status_code == 403:
                print("✗ Approver CANNOT access /customers/pending via test client (403 Forbidden)")
            else:
                print(f"Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
