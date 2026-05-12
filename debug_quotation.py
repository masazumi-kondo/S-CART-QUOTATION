import sys
sys.path.insert(0, 'c:\\Users\\3950\\SCART_Quotation')

from app import db, create_app
from app.models.quotation import Quotation
from app.models.quotation_detail import QuotationDetail
from app.routes.quotation import build_v2_result_from_details, build_summary_from_details

app = create_app()
with app.app_context():
    quotation = Quotation.query.get(46)
    details = QuotationDetail.query.filter_by(quotation_id=quotation.id).all()
    
    print(f'Testing quotation {quotation.id}:')
    print(f'Details count: {len(details)}')
    print()
    
    # Call the actual restoration functions
    v2_result = build_v2_result_from_details(details)
    summary = build_summary_from_details(quotation)
    
    print('build_v2_result_from_details result:')
    for key, val in v2_result.items():
        print(f'  {key}: {val!r}')
    
    print()
    print('build_summary_from_details result:')
    for key, val in summary.items():
        print(f'  {key}: {val!r}')
