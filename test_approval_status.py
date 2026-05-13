from app import create_app, db
from app.models.quotation import Quotation

app = create_app()
with app.app_context():
    q = Quotation.query.get(50)
    if q:
        print(f'Q-50 ID: {q.id}')
        print(f'Q-50 quotation_no: {q.quotation_no}')
        print(f'Q-50 approval_status: {q.approval_status}')
        print(f'Q-50 approval_status type: {type(q.approval_status)}')
        print(f'Q-50 approval_requested_at: {q.approval_requested_at}')
        print(f'Has approval_status attr: {hasattr(q, "approval_status")}')
    else:
        print('Q-50 not found')
