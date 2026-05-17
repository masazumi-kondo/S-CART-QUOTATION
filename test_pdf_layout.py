#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test PDF layout generation"""

import sys
import os
from app import create_app
from app.models.quotation import Quotation
from app.services.quotation_pdf_service import generate_quotation_pdf

app = create_app()

with app.app_context():
    # Test PDF generation for quotation 2
    q = Quotation.query.filter_by(id=2).first()
    if q:
        pdf_buffer = generate_quotation_pdf(q)
        if pdf_buffer:
            with open('verify_layout_2.pdf', 'wb') as f:
                f.write(pdf_buffer)
            size = os.path.getsize('verify_layout_2.pdf')
            print(f'Generated verify_layout_2.pdf: {size} bytes')
    
    # Test PDF generation for quotation 3
    q = Quotation.query.filter_by(id=3).first()
    if q:
        pdf_buffer = generate_quotation_pdf(q)
        if pdf_buffer:
            with open('verify_layout_3.pdf', 'wb') as f:
                f.write(pdf_buffer)
            size = os.path.getsize('verify_layout_3.pdf')
            print(f'Generated verify_layout_3.pdf: {size} bytes')

print('PDF generation test completed.')
