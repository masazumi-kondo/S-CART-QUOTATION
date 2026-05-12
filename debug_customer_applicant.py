#!/usr/bin/env python
"""Debug script to check customer applicant information"""

from app import create_app
from app.models.customer import Customer
from app.models.user import User

app = create_app()

print("\n" + "=" * 80)
print("デバッグ: 顧客申請者情報確認")
print("=" * 80)

with app.app_context():
    # 顧客ID 12を確認
    customer = Customer.query.get(12)
    
    if customer:
        print(f"\n顧客: {customer.id} - {customer.name}")
        print(f"  ステータス: {customer.status}")
        print(f"  requested_by_user_id: {getattr(customer, 'requested_by_user_id', 'N/A')}")
        print(f"  created_by_user_id: {getattr(customer, 'created_by_user_id', 'N/A')}")
        
        # requested_by_user_idの申請者を確認
        req_user_id = getattr(customer, 'requested_by_user_id', None)
        if req_user_id:
            req_user = User.query.get(req_user_id)
            if req_user:
                print(f"\n  申請者（requested_by）:")
                print(f"    ID: {req_user.id}")
                print(f"    ユーザーID: {req_user.login_id}")
                print(f"    メール: {req_user.email}")
                print(f"    通知: {getattr(req_user, 'receive_notifications', 'N/A')}")
                print(f"    is_active: {getattr(req_user, 'is_active', 'N/A')}")
                
                # can_receive_notification をテスト
                from app.services.notification_recipients import can_receive_notification, is_user_active
                
                is_active_result = is_user_active(req_user)
                can_receive_result = can_receive_notification(req_user)
                
                print(f"\n  関数テスト:")
                print(f"    is_user_active(): {is_active_result}")
                print(f"    can_receive_notification(): {can_receive_result}")
            else:
                print(f"\n  申請者（requested_by）: ID {req_user_id} が見つかりません")
        else:
            print(f"\n  申請者（requested_by）: 設定されていません")
        
        # 全ユーザーを表示
        print(f"\n[全ユーザー一覧]")
        all_users = User.query.all()
        for user in all_users:
            print(f"  {user.id} | {user.login_id} | {user.email} | Role: {user.role} | is_active: {getattr(user, 'is_active', 'N/A')} | notify: {getattr(user, 'receive_notifications', 'N/A')}")
        
    else:
        print(f"\n顧客ID 12 が見つかりません")

print("\n" + "=" * 80 + "\n")
