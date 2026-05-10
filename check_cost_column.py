#!/usr/bin/env python
from app import create_app, db
import sqlalchemy as sa

app = create_app()
with app.app_context():
    inspector = sa.inspect(db.engine)
    cols = [col['name'] for col in inspector.get_columns('quotation_details')]
    print("Columns in quotation_details:")
    for col in sorted(cols):
        print(f"  - {col}")
    
    # Latest detail rows
    from app.models.quotation_detail import QuotationDetail
    rows = QuotationDetail.query.order_by(QuotationDetail.id.desc()).limit(5).all()
    print("\nLatest quotation_details:")
    for row in rows:
        print(f"  id={row.id}, q_id={row.quotation_id}, price={row.price}, cost={getattr(row, 'cost', 'N/A')}")
