#!/usr/bin/env python
"""Test build_customer_approval_result_mailto_data directly"""

from app import create_app
from app.models.customer import Customer
from app.services.customer_mailto_service import build_customer_approval_result_mailto_data

app = create_app()

print("\n" + "=" * 80)
print("Testing build_customer_approval_result_mailto_data")
print("=" * 80)

with app.app_context():
    # Test with customer ID 11
    customer = Customer.query.get(11)
    
    if customer:
        print(f"\nCustomer: {customer.id} - {customer.name}")
        print(f"Status: {customer.status}")
        print(f"requested_by_user_id: {getattr(customer, 'requested_by_user_id', 'NONE')}")
        
        # Call the function
        print(f"\nCalling build_customer_approval_result_mailto_data(customer, '却下', 'テスト却下2')...")
        mailto_data = build_customer_approval_result_mailto_data(customer, "却下", "テスト却下2")
        
        print(f"\nResult:")
        if mailto_data:
            print(f"  ✓ mailto_data is NOT None")
            print(f"  Recipients: {mailto_data.get('recipients')}")
            print(f"  mailto_url exists: {bool(mailto_data.get('mailto_url'))}")
        else:
            print(f"  ✗ mailto_data is None")
    else:
        print(f"Customer ID 11 not found")

print("\n" + "=" * 80 + "\n")
