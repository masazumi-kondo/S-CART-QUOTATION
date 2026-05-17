#!/usr/bin/env python
"""PDF生成テスト"""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models.quotation import Quotation
from app.services.quotation_pdf_service import generate_quotation_pdf

# Flask アプリ作成
app = create_app()

with app.app_context():
    # Quotation ID=50 を取得
    quotation = db.session.query(Quotation).filter_by(id=50).first()
    
    if not quotation:
        print("❌ Quotation ID=50 not found")
        sys.exit(1)
    
    print(f"✓ Found Quotation ID=50: {quotation.quotation_no}")
    print(f"  - Company: {quotation.company_name}")
    print(f"  - Details: {len(quotation.details) if quotation.details else 0}")
    
    # PDF生成
    try:
        pdf_bytes = generate_quotation_pdf(quotation, customer_display_name="Test Customer")
        print(f"✓ PDF generated: {len(pdf_bytes)} bytes")
        
        # ファイルに保存
        with open("test_quotation_50.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✓ Saved to test_quotation_50.pdf")
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
