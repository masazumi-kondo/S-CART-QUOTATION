#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PDF エンドポイントのテスト - Flask テストクライアント"""

from app import create_app
from app.models.user import User

app = create_app()

with app.test_client() as client:
    # ログインユーザーを取得
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("ERROR: admin user not found")
            exit(1)
        print(f"Found user: {user.username}, id={user.id}")
    
    # テストクライアントでセッションをセット
    with client:
        # ログイン
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin1234'
        }, follow_redirects=True)
        print(f'Login response status: {response.status_code}')
        
        # セッションキーを確認
        import flask
        if hasattr(flask, 'session'):
            print(f'Session keys: {list(flask.session.keys())}')
        
        # PDF を取得
        r = client.get('/quotation/55/pdf')
        print(f'PDF status: {r.status_code}')
        print(f'PDF content-type: {r.content_type}')
        print(f'PDF size: {len(r.data)} bytes')
        if len(r.data) > 0:
            print(f'PDF first bytes: {r.data[:20]}')
            
            # ファイルに保存
            with open('test_endpoint_pdf_55_flask.pdf', 'wb') as f:
                f.write(r.data)
            print('Saved to test_endpoint_pdf_55_flask.pdf')
        else:
            print(f'Empty response: {r.data}')


