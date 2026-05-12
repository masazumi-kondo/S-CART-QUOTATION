from app import create_app
from app.models import Quotation

app = create_app()
with app.app_context():
    q = Quotation.query.get(40)
    if q:
        print('Quotation 40 Details:')
        for i, d in enumerate(q.details):
            print(f'{i}: description={repr(d.description)} | code={repr(d.code)} | label={repr(d.label)}')
