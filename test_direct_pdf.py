#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PDF エンドポイント直接テスト"""

import sys
from app import create_app
from app.services.quotation_pdf_service import generate_quotation_pdf
from app.models import Quotation

app = create_app()

with app.app_context():
    q = Quotation.query.get(55)
    if not q:
        print("Quotation 55 not found")
        sys.exit(1)
    
    # PDF を生成
    pdf_bytes = generate_quotation_pdf(q)
    print(f"PDF size: {len(pdf_bytes)} bytes")
    print(f"PDF header: {pdf_bytes[:10]}")
    
    # ファイルに保存
    with open('direct_pdf_55.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print("Saved to direct_pdf_55.pdf")
