import sys
sys.path.insert(0, '/c/Users/3950/SCART_Quotation')

from app import create_app
from app.models.quotation import Quotation

app = create_app()
with app.app_context():
    from app.routes.quotation import generate_quotation_no
    
    try:
        result = generate_quotation_no()
        print(f'generate_quotation_no() 結果: {result}')
    except Exception as e:
        print(f'エラー: {e}')
        import traceback
        traceback.print_exc()
