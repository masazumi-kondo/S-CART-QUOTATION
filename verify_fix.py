#!/usr/bin/env python
import sys
import os

# Remove cached modules
for key in list(sys.modules.keys()):
    if 'app' in key:
        del sys.modules[key]

from app import create_app
from app.models.customer import Customer

app = create_app()

with app.app_context():
    # Check actual route behavior
    with app.test_client() as client:
        response = client.get('/customers/select')
        
        # Parse HTML to count customers
        from html.parser import HTMLParser
        
        class TableRowCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_tbody = False
                self.row_count = 0
                
            def handle_starttag(self, tag, attrs):
                if tag == 'tbody':
                    self.in_tbody = True
                elif tag == 'tr' and self.in_tbody:
                    self.row_count += 1
                    
            def handle_endtag(self, tag):
                if tag == 'tbody':
                    self.in_tbody = False
        
        parser = TableRowCounter()
        parser.feed(response.data.decode('utf-8'))
        
        total_in_db = Customer.query.count()
        displayed = parser.row_count
        
        print(f"Total in DB: {total_in_db}")
        print(f"Displayed: {displayed}")
        print(f"Match: {'YES' if displayed == total_in_db else 'NO'}")
