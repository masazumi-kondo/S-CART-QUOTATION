#!/usr/bin/env python
"""Test PDF endpoint"""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    admin = db.session.query(User).filter_by(login_id='admin').first()
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = admin.id
        
        resp = client.get('/quotation/50/pdf')
        
        print(f'Status: {resp.status_code}')
        print(f'Content-Type: {resp.headers.get("Content-Type")}')
        print(f'Content-Length: {len(resp.data)}')
        print(f'First 20 bytes: {resp.data[:20]}')
        print(f'Starts with PDF header: {resp.data.startswith(b"%PDF")}')
        
        # Save to file
        with open('test_endpoint_response.pdf', 'wb') as f:
            f.write(resp.data)
        print('✓ Saved to test_endpoint_response.pdf')
