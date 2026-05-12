from app import create_app
from app.routes.quotation import get_detail_name, is_design_fee_line, is_setup_fee_line, sort_details_for_display
from app.models import Quotation

app = create_app()
with app.app_context():
    q = Quotation.query.get(40)
    if q:
        print("=== DB Order ===")
        for i, d in enumerate(q.details):
            name = get_detail_name(d)
            print(f"  [{i}] {name}")
        
        sorted_details = sort_details_for_display(q.details)
        print("\n=== Sorted Order ===")
        for i, d in enumerate(sorted_details):
            name = get_detail_name(d)
            is_design = is_design_fee_line(d)
            is_setup = is_setup_fee_line(d)
            print(f"  [{i}] {name} (design={is_design}, setup={is_setup})")
        
        # Test sort_key directly
        def sort_key(detail):
            if is_design_fee_line(detail):
                return (2, 1, getattr(detail, "id", 0))
            if is_setup_fee_line(detail):
                return (2, 2, getattr(detail, "id", 0))
            return (1, 0, getattr(detail, "id", 0))
        
        print("\n=== Sort Keys ===")
        for d in q.details:
            name = get_detail_name(d)
            key = sort_key(d)
            print(f"  {name}: {key}")
