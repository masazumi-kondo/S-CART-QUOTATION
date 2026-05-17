#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PDF 生成テスト - Quotation 55 を確認"""

import sys
from app import create_app
from app.models import Quotation
from app.services.quotation_pdf_service import generate_quotation_pdf

app = create_app()

with app.app_context():
    q = Quotation.query.get(55)
    if not q:
        print("ERROR: Quotation 55 not found")
        sys.exit(1)
    
    print(f"Quotation 55: {q.quotation_no}")
    print(f"Customer: {q.customer.name if q.customer else 'N/A'}")
    print(f"Total: {sum(d.subtotal or 0 for d in (q.details or []))}")
    
    try:
        pdf_data = generate_quotation_pdf(q)
        print(f"PDF generated: {len(pdf_data)} bytes")
        
        # Save to file for inspection
        with open('test_pdf_55_check.pdf', 'wb') as f:
            f.write(pdf_data)
        print("PDF saved to test_pdf_55_check.pdf")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
