#!/usr/bin/env python
"""
Debug script to test V2 result and summary restoration from detail rows.
"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.models.quotation import Quotation
from app.models.quotation_detail import QuotationDetail

# Create Flask app context
app = create_app()
with app.app_context():
    # Get quotation 46
    quotation = Quotation.query.get(46)
    if not quotation:
        print("Quotation 46 not found")
        sys.exit(1)
    
    print(f"\nQuotation ID: {quotation.id}")
    print(f"Total details: {len(quotation.details)}")
    
    # Print all details
    for i, d in enumerate(quotation.details):
        name = getattr(d, 'label', getattr(d, 'description', ''))
        subtotal = getattr(d, 'subtotal', 0)
        cost = getattr(d, 'cost', 0)
        print(f"  Detail {i}: label={d.label}, description={d.description}, subtotal={subtotal}, cost={cost}")
    
    # Test helper functions
    from app.routes.quotation import get_detail_name, is_design_fee_line, is_setup_fee_line
    from app.routes.quotation import build_v2_result_from_details, build_summary_from_details
    
    print("\n--- Testing helpers ---")
    for i, d in enumerate(quotation.details):
        name = get_detail_name(d)
        is_design = is_design_fee_line(d)
        is_setup = is_setup_fee_line(d)
        print(f"Detail {i}: name='{name}', is_design={is_design}, is_setup={is_setup}")
    
    print("\n--- Testing build_v2_result_from_details ---")
    v2_result = build_v2_result_from_details(quotation.details)
    print(f"V2 Result: {v2_result}")
    
    print("\n--- Testing build_summary_from_details ---")
    summary = build_summary_from_details(quotation)
    print(f"Summary: {summary}")
