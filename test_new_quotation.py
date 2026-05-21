#!/usr/bin/env python
import sys
sys.path.insert(0, 'c:\\Users\\3950\\SCART_Quotation')

from app import create_app

# Create app context
app = create_app()

# Test with client
with app.test_client() as client:
    with app.app_context():
        # Test new quotation creation with save_action=list
        print("Testing NEW quotation POST with save_action=list...")
        
        # Prepare minimal form data for NEW quotation
        form_data = {
            'company_name': 'テスト新規顧客',
            'contact_name': 'test',
            'project_name': 'テスト新規プロジェクト',
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
            # No customer_id, no edit_quotation_id - this is NEW
            'remarks': 'test new',
        }
        
        response = client.post('/quotation/new', data=form_data, follow_redirects=False)
        print(f"Response status: {response.status_code}")
        print(f"Response location: {response.location}")
        
        if response.status_code == 302 and response.location == '/quotations':
            print("✅ NEW quotation: save_action='list' redirects to /quotations")
        else:
            print(f"❌ NEW quotation: Expected 302 /quotations, got {response.status_code} {response.location}")

        # Also test save_action=stay for new quotation
        print("\nTesting NEW quotation POST with save_action=stay...")
        form_data['save_action'] = 'stay'
        
        response = client.post('/quotation/new', data=form_data, follow_redirects=False)
        print(f"Response status: {response.status_code}")
        print(f"Response location: {response.location}")
        
        if response.status_code == 302 and '/quotation/' in response.location and '/edit' in response.location:
            print("✅ NEW quotation: save_action='stay' redirects to /quotation/<id>/edit")
        else:
            print(f"❌ NEW quotation: Expected 302 /quotation/<id>/edit, got {response.status_code} {response.location}")
