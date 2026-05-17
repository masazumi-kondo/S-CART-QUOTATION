#!/usr/bin/env python
"""正式見積書PDF生成テスト"""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models.quotation import Quotation
from app.models.user import User

app = create_app()

with app.app_context():
    # テスト対象の見積を取得
    print("=== 利用可能な見積一覧 ===")
    quotations = db.session.query(Quotation).limit(10).all()
    
    for q in quotations:
        discount = q.discount_amount or 0
        has_discount = "有" if discount > 0 else "無"
        print(f"ID={q.id}, No={q.quotation_no}, 顧客={q.company_name}, 割引={has_discount}, 作成者={q.estimator_name}")
    
    # 値引きあり、なしの見積を探す
    with_discount = None
    without_discount = None
    
    for q in quotations:
        if (q.discount_amount or 0) > 0 and with_discount is None:
            with_discount = q
        if (q.discount_amount or 0) == 0 and without_discount is None:
            without_discount = q
    
    print("\n=== PDF生成テスト ===")
    
    test_quotations = []
    if with_discount:
        test_quotations.append(("値引きあり", with_discount))
    if without_discount:
        test_quotations.append(("値引きなし", without_discount))
    
    if not test_quotations:
        print("❌ テスト対象の見積が見つかりません")
        sys.exit(1)
    
    for label, q in test_quotations:
        print(f"\n📄 {label} (ID={q.id})")
        
        try:
            from app.services.quotation_pdf_service import generate_quotation_pdf
            
            customer_name = q.company_name or "未設定"
            pdf_bytes = generate_quotation_pdf(q, customer_display_name=customer_name)
            
            print(f"  ✓ PDF生成成功：{len(pdf_bytes)} bytes")
            print(f"  ✓ PDF Header: {pdf_bytes[:4]}")
            
            # テストファイルに保存
            filename = f"test_quotation_{q.id}_{label.replace('/', '_')}.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_bytes)
            print(f"  ✓ 保存：{filename}")
            
        except Exception as e:
            print(f"  ❌ エラー：{e}")
            import traceback
            traceback.print_exc()

print("\n✓ テスト完了")
