#!/usr/bin/env python
import sys
sys.path.insert(0, 'c:\\Users\\3950\\SCART_Quotation')

from app import create_app

app = create_app()

with app.test_client() as client:
    with app.app_context():
        # Test 1: Empty search (should show all customers)
        print("=" * 60)
        print("TEST 1: Empty search - should show all customers")
        print("=" * 60)
        
        response = client.get('/customers/select')
        assert response.status_code == 200
        
        from app.models.customer import Customer
        total_customers = Customer.query.count()
        print(f"Total customers in DB: {total_customers}")
        
        # Parse response to count displayed customers
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find alert message with count
        alert = soup.find('div', class_='alert-info')
        if alert:
            text = alert.get_text(strip=True)
            print(f"Alert text: {text}")
        
        # Count table rows
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]  # Skip header
            displayed_count = len(rows)
            print(f"Displayed customers: {displayed_count}")
            print(f"Match: {'✅ YES' if displayed_count == total_customers else '❌ NO'}")
        else:
            print("❌ No table found")
        
        # Test 2: Keyword search
        print("\n" + "=" * 60)
        print("TEST 2: Keyword search - should filter results")
        print("=" * 60)
        
        response = client.get('/customers/select?q=IHI')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:]
            displayed_count = len(rows)
            print(f"Search keyword: 'IHI'")
            print(f"Displayed customers: {displayed_count}")
            if displayed_count > 0:
                print("First result:", rows[0].find_all('td')[0].get_text(strip=True))
        
        # Test 3: Check status distribution
        print("\n" + "=" * 60)
        print("TEST 3: Customer status distribution")
        print("=" * 60)
        
        from sqlalchemy import func
        result = Client.query.session.query(
            Customer.status, func.count(Customer.id)
        ).group_by(Customer.status).all()
        
        for status, count in result:
            print(f"  Status '{status}': {count}")
