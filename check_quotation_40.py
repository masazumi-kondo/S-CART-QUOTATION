from app import create_app, db
from app.models import Quotation

app = create_app()
with app.app_context():
    q = Quotation.query.get(40)
    if q:
        print(f"Quotation 40:")
        print(f"  ID: {q.id}")
        print(f"  quotation_no: {q.quotation_no}")
        print(f"  Details count: {len(q.details)}")
        print(f"\nDetails (in DB order):")
        for i, d in enumerate(q.details):
            print(f"  [{i}] label='{d.label}'")
            print(f"      product_id={d.product_id} | quantity={d.quantity}")
            print(f"      price={d.price} | subtotal={d.subtotal}")
            if d.product:
                print(f"      product.name='{d.product.name}'")
    else:
        print("Quotation 40 not found")
