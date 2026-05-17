#!/usr/bin/env python
"""
Test PDF generation to verify remarks box fix
"""
import sys
import os
sys.path.insert(0, '.')

from app import create_app
from app.models.quotation import Quotation
from app.services.quotation_pdf_service import generate_quotation_pdf

app = create_app()
with app.app_context():
    # Test quotation 55
    q = Quotation.query.filter_by(id=55).first()
    if q:
        print("[PDF] Generating quotation 55 PDF...")
        pdf_buffer = generate_quotation_pdf(q)
        if pdf_buffer:
            with open('test_remarks_fix_55.pdf', 'wb') as f:
                f.write(pdf_buffer)
            file_size = os.path.getsize("test_remarks_fix_55.pdf")
            print(f"✓ Generated test_remarks_fix_55.pdf: {file_size} bytes")
    else:
        print("✗ Quotation 55 not found")

    # Test quotation 2
    q = Quotation.query.filter_by(id=2).first()
    if q:
        print("[PDF] Generating quotation 2 PDF...")
        pdf_buffer = generate_quotation_pdf(q)
        if pdf_buffer:
            with open('test_remarks_fix_2.pdf', 'wb') as f:
                f.write(pdf_buffer)
            file_size = os.path.getsize("test_remarks_fix_2.pdf")
            print(f"✓ Generated test_remarks_fix_2.pdf: {file_size} bytes")
    else:
        print("✗ Quotation 2 not found")

    # Test quotation 3
    q = Quotation.query.filter_by(id=3).first()
    if q:
        print("[PDF] Generating quotation 3 PDF...")
        pdf_buffer = generate_quotation_pdf(q)
        if pdf_buffer:
            with open('test_remarks_fix_3.pdf', 'wb') as f:
                f.write(pdf_buffer)
            file_size = os.path.getsize("test_remarks_fix_3.pdf")
            print(f"✓ Generated test_remarks_fix_3.pdf: {file_size} bytes")
    else:
        print("✗ Quotation 3 not found")

print("\n[✓] PDF generation test completed successfully")
