#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, '.')

from app import create_app
from app.models.quotation import Quotation
from app.services.quotation_pdf_service import generate_quotation_pdf

app = create_app()
with app.app_context():
    for qid in [55, 2, 3]:
        q = Quotation.query.filter_by(id=qid).first()
        if q:
            pdf_buffer = generate_quotation_pdf(q)
            if pdf_buffer:
                filename = f'test_remarks_fix_{qid}.pdf'
                with open(filename, 'wb') as f:
                    f.write(pdf_buffer)
                file_size = os.path.getsize(filename)
                print(f"Generated {filename}: {file_size} bytes")

print("PDF generation completed")
