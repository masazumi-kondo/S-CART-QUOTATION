#!/usr/bin/env python
"""Check which user created each customer"""

from app import create_app
from app.models.customer import Customer
from app.models.user import User

app = create_app()

print("\n" + "=" * 80)
print("顧客と申請者のマッピング")
print("=" * 80)

with app.app_context():
    customers = Customer.query.all()
    
    for cust in customers:
        req_id = getattr(cust, 'requested_by_user_id', None)
        
        if req_id:
            req_user = User.query.get(req_id)
            if req_user:
                req_email = req_user.email
                req_name = req_user.login_id
            else:
                req_email = "NOT FOUND"
                req_name = "NOT FOUND"
        else:
            req_email = "NO USER ID"
            req_name = "NO USER ID"
        
        print(f"\nCustomer ID {cust.id}")
        print(f"  Name: {cust.name}")
        print(f"  Status: {cust.status}")
        print(f"  requested_by_user_id: {req_id}")
        print(f"  Applicant Name: {req_name}")
        print(f"  Applicant Email: {req_email}")

print("\n" + "=" * 80 + "\n")
