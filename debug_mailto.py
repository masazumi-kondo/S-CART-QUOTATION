#!/usr/bin/env python
"""Debug script to check customer approval mailto data generation"""

from app import create_app
from app.models.user import User
from app.services.notification_recipients import (
    get_customer_approval_admin_recipients,
)
from app.services.customer_mailto_service import (
    build_customer_approval_request_mailto_data,
)

app = create_app()

print("\n" + "=" * 80)
print("デバッグ: mailto設定確認")
print("=" * 80)

with app.app_context():
    # 1. MAIL_PROVIDER設定確認
    mail_provider = app.config.get("MAIL_PROVIDER", "")
    print(f"\n1. MAIL_PROVIDER: '{mail_provider}'")
    print(f"   期待値: 'mailto'")
    if mail_provider.lower() != "mailto":
        print(f"   ❌ エラー: MAIL_PROVIDER が 'mailto' に設定されていません")
    
    # 2. データベース接続確認
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    print(f"\n2. Database URI: {db_uri}")
    
    # 3. User テーブル確認
    try:
        all_users = User.query.all()
        print(f"\n3. 全ユーザー数: {len(all_users)}")
        for user in all_users:
            print(f"   - ID:{user.id} | User:{user.login_id} | Email:{user.email} | Role:{user.role} | Active:{user.active} | Notify:{user.receive_notifications}")
    except Exception as e:
        print(f"\n3. ❌ User.query失敗: {e}")
    
    # 4. 管理者のみ確認
    try:
        admins = User.query.filter_by(role="admin").all()
        print(f"\n4. 管理者ユーザー数: {len(admins)}")
        for admin in admins:
            print(f"   - ID:{admin.id} | User:{admin.login_id} | Email:{admin.email} | Active:{admin.active} | Notify:{admin.receive_notifications}")
    except Exception as e:
        print(f"\n4. ❌ Admin query失敗: {e}")
    
    # 5. get_customer_approval_admin_recipients() テスト
    try:
        recipients = get_customer_approval_admin_recipients()
        print(f"\n5. get_customer_approval_admin_recipients():")
        print(f"   結果: {recipients}")
        if not recipients:
            print(f"   ❌ 管理者メールアドレスが見つかりません")
        else:
            print(f"   ✓ {len(recipients)}個のメールアドレス")
    except Exception as e:
        print(f"\n5. ❌ 関数実行失敗: {e}")
    
    # 6. ダミー顧客でmailto_data テスト
    try:
        from app.models.customer import Customer
        
        # テスト用顧客オブジェクト作成（DBに保存しない）
        test_customer = Customer()
        test_customer.id = 999
        test_customer.name = "テスト顧客"
        test_customer.requested_by_user_id = None
        
        mailto_data = build_customer_approval_request_mailto_data(test_customer)
        print(f"\n6. build_customer_approval_request_mailto_data():")
        if mailto_data:
            print(f"   ✓ mailto_url取得成功")
            print(f"   Recipients: {mailto_data.get('recipients')}")
        else:
            print(f"   ❌ 結果がNone")
    except Exception as e:
        print(f"\n6. ❌ 関数実行失敗: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80 + "\n")
