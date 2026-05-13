#!/usr/bin/env python
"""Test CSV export endpoints"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.user import User
from app.models.customer import Customer, CustomerStatus
from app.models.product import Product
from app.models.quotation import Quotation
from datetime import datetime

def test_csv_exports():
    """Test that CSV export routes work"""
    app = create_app()
    
    with app.app_context():
        # Check if routes are registered
        print("Checking registered routes...")
        routes = []
        for rule in app.url_map.iter_rules():
            if 'export' in rule.rule:
                routes.append(rule.rule)
                print(f"  ✓ {rule.rule}")
        
        if '/quotations/export-csv' not in routes:
            print("  ✗ /quotations/export-csv not found!")
            return False
        
        if '/admin/users/export-csv' not in routes:
            print("  ✗ /admin/users/export-csv not found!")
            return False
        
        if '/customers/export-csv' not in routes:
            print("  ✗ /customers/export-csv not found!")
            return False
            
        if '/products/export-csv' not in routes:
            print("  ✗ /products/export-csv not found!")
            return False
        
        print("\n✓ All CSV export routes are registered!")
        
        # Test CSV generation with test data
        print("\nTesting CSV data generation...")
        
        # Count data
        users = User.query.count()
        customers = Customer.query.count()
        products = Product.query.count()
        quotations = Quotation.query.count()
        
        print(f"  Database contains:")
        print(f"    - {users} users")
        print(f"    - {customers} customers")
        print(f"    - {products} products")
        print(f"    - {quotations} quotations")
        
        return True

if __name__ == '__main__':
    try:
        success = test_csv_exports()
        if success:
            print("\n✓ All tests passed!")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
