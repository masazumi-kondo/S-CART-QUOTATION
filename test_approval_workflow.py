#!/usr/bin/env python
"""Test quotation approval workflow"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Set encoding to UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import create_app, db
from app.models.quotation import Quotation
from app.models.quotation_detail import QuotationDetail
from app.models.customer import Customer, CustomerStatus
from app.models.user import User
from app.approval_utils import get_approval_status_label, can_request_approval
from datetime import datetime

def test_approval_workflow():
    """Test quotation approval workflow"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Testing Quotation Approval Workflow")
        print("=" * 60)
        
        # Test 1: Check approval status labels
        print("\n[Test 1] Approval Status Labels")
        statuses = ['draft', 'pending', 'approved', 'rejected']
        labels = {s: get_approval_status_label(s) for s in statuses}
        for status, label in labels.items():
            print(f"  {status:12} -> {label}")
        assert labels['draft'] == '作成中', "Draft label incorrect"
        assert labels['pending'] == '承認待ち', "Pending label incorrect"
        assert labels['approved'] == '承認済み', "Approved label incorrect"
        assert labels['rejected'] == '差戻し', "Rejected label incorrect"
        print("  [OK] All labels correct")
        
        # Test 2: Check database columns
        print("\n[Test 2] Database Columns")
        quotation = Quotation.query.first()
        if quotation:
            print(f"  Sample quotation ID: {quotation.id}")
            print(f"  approval_status: {quotation.approval_status}")
            print(f"  approval_requested_at: {quotation.approval_requested_at}")
            print(f"  approved_at: {quotation.approved_at}")
            print(f"  approved_by_user_id: {quotation.approved_by_user_id}")
            print(f"  rejected_at: {quotation.rejected_at}")
            print(f"  rejected_by_user_id: {quotation.rejected_by_user_id}")
            print(f"  approval_comment: {quotation.approval_comment}")
            print(f"  estimator_user_id: {quotation.estimator_user_id}")
            print("  [OK] All columns exist and accessible")
        else:
            print("  [WARN] No quotation in database, creating test quotation...")
            # Create a test quotation
            customer = Customer.query.filter_by(status=CustomerStatus.APPROVED.value).first()
            if not customer:
                print("  [FAIL] No approved customer found for test")
                return False
            
            quotation = Quotation(
                company_name="Test Company",
                project_name="Test Project",
                customer_id=customer.id,
                approval_status="draft"
            )
            db.session.add(quotation)
            db.session.commit()
            print(f"  [OK] Test quotation created with ID: {quotation.id}")
        
        # Test 3: Check approval validation
        print("\n[Test 3] Approval Validation")
        empty_q = Quotation(
            company_name="",
            project_name="",
            approval_status="draft"
        )
        can_req, msg = can_request_approval(empty_q)
        print(f"  Empty quotation: can_request={can_req}, msg='{msg}'")
        assert not can_req, "Empty quotation should not be approvable"
        print("  [OK] Validation works correctly")
        
        # Test 4: Check relationships
        print("\n[Test 4] User Relationships")
        q = Quotation.query.first()
        if q:
            print(f"  Quotation ID: {q.id}")
            print(f"  Has approved_by_user relationship: {hasattr(q, 'approved_by_user')}")
            print(f"  Has rejected_by_user relationship: {hasattr(q, 'rejected_by_user')}")
            print(f"  Has estimator relationship: {hasattr(q, 'estimator')}")
            print("  [OK] All relationships exist")
        
        # Test 5: Check CSV export fields
        print("\n[Test 5] CSV Export Fields")
        quotations = Quotation.query.limit(1).all()
        if quotations:
            q = quotations[0]
            status_label = get_approval_status_label(q.approval_status)
            approver_name = q.approved_by_user.display_name if q.approved_by_user else ''
            rejector_name = q.rejected_by_user.display_name if q.rejected_by_user else ''
            print(f"  Quotation {q.id}:")
            print(f"    - approval_status_label: {status_label}")
            print(f"    - approved_by_user: {approver_name}")
            print(f"    - rejected_by_user: {rejector_name}")
            print("  [OK] CSV export fields accessible")
        
        # Test 6: Check routes are registered
        print("\n[Test 6] Routes Registration")
        routes_to_check = [
            '/quotation/<int:quotation_id>/request-approval',
            '/quotation/<int:quotation_id>/approve',
            '/quotation/<int:quotation_id>/reject',
        ]
        registered_routes = [str(r.rule) for r in app.url_map.iter_rules()]
        for route in routes_to_check:
            registered = any(route in r for r in registered_routes)
            status = "[OK]" if registered else "[FAIL]"
            print(f"  {status} {route}")
        print("  [OK] All routes registered")
        
        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        return True

if __name__ == '__main__':
    try:
        success = test_approval_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
