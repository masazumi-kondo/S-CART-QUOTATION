from app import create_app, db
from app.models.quotation import Quotation

app = create_app()
with app.app_context():
    q = Quotation.query.order_by(Quotation.id.desc()).first()
    if q:
        print(f'ID: {q.id}, Company: {q.company_name}, Project: {q.project_name}, valid_until: {q.valid_until}')
    else:
        print('No quotation found')
