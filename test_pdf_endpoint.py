#!/usr/bin/env python
"""PDF エンドポイントテスト"""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models.user import User

# Flask アプリ作成
app = create_app()

with app.app_context():
    # テスト用ユーザー作成（admin ユーザーがあればそれを使用）
    admin = db.session.query(User).filter_by(login_id='admin').first()
    
    if not admin:
        print("❌ Admin user not found")
        sys.exit(1)
    
    print(f"✓ Found admin user: {admin.login_id}")
    
    # テストクライアント作成
    client = app.test_client()
    
    # ログイン
    with app.test_client() as c:
        # セッションにユーザーを手動設定（簡単なテスト方法）
        with c.session_transaction() as session:
            session['user_id'] = admin.id
        
        # PDF エンドポイントへのリクエスト
        response = c.get('/quotation/50/pdf')
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Content-Type: {response.content_type}")
        print(f"Response Length: {len(response.data)} bytes")
        
        if response.status_code == 200:
            print("✓ PDF endpoint returned 200 OK")
            if response.content_type == 'application/pdf':
                print("✓ Content-Type is application/pdf")
                # PDFが有効か確認
                if response.data.startswith(b'%PDF'):
                    print("✓ PDF starts with %PDF header")
                    with open("test_pdf_from_endpoint.pdf", "wb") as f:
                        f.write(response.data)
                    print("✓ Saved to test_pdf_from_endpoint.pdf")
                else:
                    print("❌ PDF does not start with %PDF header")
                    print(f"First bytes: {response.data[:100]}")
            else:
                print(f"❌ Content-Type is {response.content_type}, expected application/pdf")
        else:
            print(f"❌ PDF endpoint returned {response.status_code}")
            print(f"Response data: {response.data[:500]}")
