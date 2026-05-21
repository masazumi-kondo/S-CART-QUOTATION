from app import create_app

app = create_app()

with app.test_client() as client:
    response = client.get('/customers/select')
    html = response.data.decode('utf-8')
    
    # Count rows
    import re
    tbody = re.search(r'<tbody>(.*?)</tbody>', html, re.DOTALL)
    if tbody:
        rows = tbody.group(1).count('<tr>')
        print(f'Displayed rows: {rows}')
    
    # Check summary message
    summary = re.search(r'(\d+)件の顧客', html)
    if summary:
        print(f'Summary says: {summary.group(1)} customers')
