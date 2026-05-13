#!/usr/bin/env python
"""
Simple syntax and structure validation test for unified notification system
"""
import sys
import os
from pathlib import Path
from datetime import datetime

def test_files_structure():
    """Verify all modified files exist and have correct structure"""
    print("=" * 70)
    print("UNIFIED NOTIFICATION SYSTEM - VALIDATION TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: notification_recipients.py
    print("[TEST 1] notification_recipients.py has unified function")
    try:
        path = Path("app/services/notification_recipients.py")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("def get_approval_notification_users()", "Unified function definition"),
            ("User.query.filter_by(role=\"admin\"", "Filters for admin role"),
            ("receive_notifications=True", "Filters for enabled notifications"),
            ("is_user_active(user)", "Checks user active status"),
            ("def get_customer_approval_admin_recipients()", "Backward compatibility function"),
            ("get_approval_notification_users()", "Uses unified function"),
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
                tests_passed += 1
            else:
                print(f"  ✗ {desc}")
                tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed to read file: {e}")
        tests_failed += 1
    
    # Test 2: user_form.html template
    print("\n[TEST 2] user_form.html has updated label")
    try:
        path = Path("app/templates/admin/user_form.html")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("承認依頼通知を受け取る", "New unified label"),
            ("顧客マスタ承認依頼と見積承認依頼", "Supplementary text about both approval types"),
            ("small class=\"form-text text-muted", "Styling for supplementary text"),
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
                tests_passed += 1
            else:
                print(f"  ✗ {desc}")
                tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed to read file: {e}")
        tests_failed += 1
    
    # Test 3: customer_email_notification_service.py
    print("\n[TEST 3] customer notification service updated")
    try:
        path = Path("app/services/customer_email_notification_service.py")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("get_approval_notification_users", "Imports unified function"),
            ("users = get_approval_notification_users()", "Calls unified function"),
            ("recipients = [user.email for user in users", "Extracts emails from users"),
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
                tests_passed += 1
            else:
                print(f"  ✗ {desc}")
                tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed to read file: {e}")
        tests_failed += 1
    
    # Test 4: quotation_email_notification_service.py
    print("\n[TEST 4] quotation notification service created")
    try:
        path = Path("app/services/quotation_email_notification_service.py")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("def notify_quotation_approval_request(quotation):", "Notification function"),
            ("get_approval_notification_users", "Uses unified function"),
            ("見積の承認依頼があります", "Quotation-specific message"),
            ("send_bulk_email(recipients", "Sends emails to recipients"),
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                print(f"  ✓ {desc}")
                tests_passed += 1
            else:
                print(f"  ✗ {desc}")
                tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed to read file: {e}")
        tests_failed += 1
    
    # Test 5: quotation.py route
    print("\n[TEST 5] quotation route sends notification")
    try:
        path = Path("app/routes/quotation.py")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the function
        func_start = content.find("def quotation_request_approval(quotation_id):")
        if func_start == -1:
            print(f"  ✗ Function quotation_request_approval not found")
            tests_failed += 1
        else:
            func_end = content.find("\n@", func_start + 1)
            func_content = content[func_start:func_end]
            
            checks = [
                ("db.session.commit()", "Commits changes before notification"),
                ("notify_quotation_approval_request", "Sends notification"),
                ("from app.services.quotation_email_notification_service", "Imports notification service"),
            ]
            
            for check_str, desc in checks:
                if check_str in func_content:
                    print(f"  ✓ {desc}")
                    tests_passed += 1
                else:
                    print(f"  ✗ {desc}")
                    tests_failed += 1
    except Exception as e:
        print(f"  ✗ Failed to read file: {e}")
        tests_failed += 1
    
    # Test 6: Python imports
    print("\n[TEST 6] Python modules import correctly")
    try:
        from app.services.notification_recipients import (
            get_approval_notification_users,
            get_customer_approval_admin_recipients
        )
        print(f"  ✓ notification_recipients functions import")
        tests_passed += 1
        
        from app.services.customer_email_notification_service import notify_customer_approval_request
        print(f"  ✓ customer notification service imports")
        tests_passed += 1
        
        from app.services.quotation_email_notification_service import notify_quotation_approval_request
        print(f"  ✓ quotation notification service imports")
        tests_passed += 1
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        tests_failed += 3
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Total:  {tests_passed + tests_failed}")
    
    if tests_failed == 0:
        print("\n✓ All validation checks PASSED!")
        return 0
    else:
        print(f"\n✗ {tests_failed} validation check(s) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(test_files_structure())
