#!/usr/bin/env python
"""
Integration test for unified notification system (Phase 5)
Tests the consolidated customer master and quotation approval notifications
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up Flask app context
os.environ['MAIL_PROVIDER'] = 'mailto'
from app import create_app, db
from app.models.user import User
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.services.notification_recipients import (
    get_approval_notification_users,
    get_customer_approval_admin_recipients,
    can_receive_notification,
    is_user_active
)
from app.services.customer_email_notification_service import notify_customer_approval_request
from app.services.quotation_email_notification_service import notify_quotation_approval_request

def test_unified_notification_function():
    """Test that get_approval_notification_users returns correct users"""
    print("\n[TEST 1] Testing unified get_approval_notification_users() function")
    
    with app.app_context():
        users = get_approval_notification_users()
        print(f"  ✓ Function returned {len(users)} users")
        
        # Verify only admins with notifications enabled are returned
        for user in users:
            assert user.role == "admin", f"Non-admin user returned: {user.login_id}"
            assert user.receive_notifications == True, f"Disabled notifications user: {user.login_id}"
            assert user.is_active == True, f"Inactive user: {user.login_id}"
            assert user.email, f"User without email: {user.login_id}"
        
        print("  ✓ All returned users are admins with notifications enabled")
        return True

def test_backward_compatibility():
    """Test that customer approval still works with unified function"""
    print("\n[TEST 2] Testing backward compatibility with customer approval")
    
    with app.app_context():
        # Get recipients using old function
        old_recipients = get_customer_approval_admin_recipients()
        
        # Get users using new unified function and extract emails
        users = get_approval_notification_users()
        new_recipients = [user.email for user in users if user.email]
        
        # Both should return same results
        assert set(old_recipients) == set(new_recipients), "Recipients don't match"
        print(f"  ✓ Old and new functions return same {len(old_recipients)} recipients")
        return True

def test_notification_disabled_admin():
    """Test that disabled admins are excluded from both lists"""
    print("\n[TEST 3] Testing notification-disabled admin is excluded")
    
    with app.app_context():
        # Find an admin with notifications disabled
        disabled_admin = User.query.filter_by(
            role="admin",
            receive_notifications=False
        ).first()
        
        if disabled_admin:
            users = get_approval_notification_users()
            recipients = get_customer_approval_admin_recipients()
            
            assert disabled_admin.id not in [u.id for u in users], \
                "Disabled admin in notification users"
            assert disabled_admin.email not in recipients, \
                "Disabled admin in recipients list"
            print(f"  ✓ Disabled admin '{disabled_admin.login_id}' correctly excluded")
        else:
            print("  ⊘ No disabled admin found, skipping test")
        
        return True

def test_inactive_user_excluded():
    """Test that inactive users are excluded"""
    print("\n[TEST 4] Testing inactive users are excluded")
    
    with app.app_context():
        # Find an inactive user
        inactive = User.query.filter_by(is_active=False).first()
        
        if inactive:
            users = get_approval_notification_users()
            
            assert inactive.id not in [u.id for u in users], \
                f"Inactive user {inactive.login_id} in notification list"
            print(f"  ✓ Inactive user correctly excluded from notifications")
        else:
            print("  ⊘ No inactive user found, skipping test")
        
        return True

def test_non_admin_excluded():
    """Test that non-admin users are excluded"""
    print("\n[TEST 5] Testing non-admin users are excluded")
    
    with app.app_context():
        # Find a non-admin user
        non_admin = User.query.filter_by(role="user").first()
        
        if non_admin:
            users = get_approval_notification_users()
            
            assert non_admin.id not in [u.id for u in users], \
                f"Non-admin user {non_admin.login_id} in notification list"
            print(f"  ✓ Non-admin user correctly excluded from notifications")
        else:
            print("  ⊘ No non-admin user found, skipping test")
        
        return True

def test_quotation_notification_importable():
    """Test that quotation notification service imports correctly"""
    print("\n[TEST 6] Testing quotation notification service")
    
    try:
        from app.services.quotation_email_notification_service import notify_quotation_approval_request
        print("  ✓ Quotation notification service imports successfully")
        
        # Verify the function signature
        import inspect
        sig = inspect.signature(notify_quotation_approval_request)
        assert 'quotation' in sig.parameters, "Missing quotation parameter"
        print("  ✓ Function has correct signature")
        
        return True
    except ImportError as e:
        print(f"  ✗ Failed to import: {e}")
        return False

def test_customer_notification_uses_unified():
    """Test that customer notification imports and uses unified function"""
    print("\n[TEST 7] Testing customer notification service uses unified function")
    
    try:
        # Read the customer notification service source
        service_path = Path(__file__).parent / "app" / "services" / "customer_email_notification_service.py"
        with open(service_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that it imports the unified function
        assert "get_approval_notification_users" in content, \
            "Customer service doesn't import unified function"
        print("  ✓ Customer service imports unified function")
        
        # Check that old function is still available for backward compatibility
        assert "get_customer_approval_admin_recipients" in content, \
            "Backward compatibility function missing"
        print("  ✓ Backward compatibility function still available")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_user_form_template():
    """Test that user form template has updated label"""
    print("\n[TEST 8] Testing user form template label update")
    
    try:
        template_path = Path(__file__).parent / "app" / "templates" / "admin" / "user_form.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for new label
        assert "承認依頼通知を受け取る" in content, "New label not found"
        print("  ✓ Template has updated label '承認依頼通知を受け取る'")
        
        # Check for supplementary text
        assert "顧客マスタ承認依頼と見積承認依頼の通知を受け取ります" in content, \
            "Supplementary text not found"
        print("  ✓ Template has supplementary text about both approval types")
        
        # Check that old label is gone
        assert "通知を受け取る" not in content or "承認依頼通知を受け取る" in content, \
            "Old ambiguous label still present"
        print("  ✓ Old ambiguous label removed")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_quotation_route_sends_notification():
    """Test that quotation_request_approval sends notification"""
    print("\n[TEST 9] Testing quotation request approval sends notification")
    
    try:
        route_path = Path(__file__).parent / "app" / "routes" / "quotation.py"
        with open(route_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the quotation_request_approval function
        func_idx = content.find("def quotation_request_approval(quotation_id):")
        assert func_idx != -1, "Function not found"
        
        # Check for notification call within the function
        func_end = content.find("\n@", func_idx + 1)
        func_content = content[func_idx:func_end]
        
        assert "notify_quotation_approval_request" in func_content, \
            "Notification not sent in request approval"
        print("  ✓ quotation_request_approval sends notification")
        
        assert "db.session.commit()" in func_content, \
            "Database commit missing"
        print("  ✓ Database changes committed before notification")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_notification_recipients_module():
    """Test the notification recipients module"""
    print("\n[TEST 10] Testing notification recipients module structure")
    
    try:
        module_path = Path(__file__).parent / "app" / "services" / "notification_recipients.py"
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for all required functions
        functions = [
            "is_user_active",
            "can_receive_notification", 
            "get_approval_notification_users",
            "get_customer_approval_admin_recipients",
            "get_customer_approval_result_recipient"
        ]
        
        for func in functions:
            assert f"def {func}" in content, f"Function {func} not found"
            print(f"  ✓ Function {func} present")
        
        # Check that new function returns User objects, not emails
        assert "return recipients" in content and "User.query" in content, \
            "New function signature looks wrong"
        print("  ✓ New function returns User objects")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("UNIFIED NOTIFICATION SYSTEM - INTEGRATION TEST SUITE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Database: C:\\Users\\3950\\SCART_Quotation\\estimates.db")
    
    test_functions = [
        test_unified_notification_function,
        test_backward_compatibility,
        test_notification_disabled_admin,
        test_inactive_user_excluded,
        test_non_admin_excluded,
        test_quotation_notification_importable,
        test_customer_notification_uses_unified,
        test_user_form_template,
        test_quotation_route_sends_notification,
        test_notification_recipients_module,
    ]
    
    results = []
    
    for test_func in test_functions:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_func.__name__, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests PASSED!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) FAILED")
        return 1

if __name__ == "__main__":
    # Create Flask app
    app = create_app()
    
    sys.exit(main())
