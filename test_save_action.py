#!/usr/bin/env python
import sys
sys.path.insert(0, 'c:\\Users\\3950\\SCART_Quotation')

from app import create_app
from flask import url_for
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Create app context
app = create_app()

# Test with client
with app.test_client() as client:
    with app.app_context():
        # First, check if quotation 10 is editable
        from app.models.quotation import Quotation
        from app.models.customer import Customer, CustomerStatus
        
        q = Quotation.query.get(10)
        if q:
            print(f"Quotation 10: customer_id={q.customer_id}, project_name={q.project_name}")
            
            # Check customer
            c = Customer.query.get(q.customer_id)
            if c:
                print(f"Customer: name={c.name}, status={c.status}, is_approved={c.is_approved}")
        
        # Now test POST with save_action=list
        print("\nTesting POST with save_action=list...")
        
        # Prepare minimal form data
        form_data = {
            'edit_quotation_id': '10',
            'company_name': 'IHI原動機',
            'contact_name': 'test',
            'project_name': 'IHI原動機向けV1000',
            'delivery_date': '',
            'delivery_terms': '',
            'payment_terms': '',
            'valid_days': '',
            'v2_vehicle_count': '1',
            'v2_pickup_count': '1',
            'v2_dropoff_count': '1',
            'v2_area_short_m': '10',
            'v2_area_long_m': '20',
            'v2_route_complexity': 'standard',
            'v2_merge_level': 'standard',
            'product_id[]': '',
            'description[]': '現地セットアップ費',
            'quantity[]': '1',
            'unit_price[]': '',
            'subtotal[]': '100',
            'cost[]': '0',
            'save_action': 'list',
            'customer_id': '1',
            'remarks': 'test',
        }
        
        response = client.post('/quotation/new', data=form_data, follow_redirects=False)
        print(f"Response status: {response.status_code}")
        print(f"Response location: {response.location}")
        print(f"Response headers: {dict(response.headers)}")
