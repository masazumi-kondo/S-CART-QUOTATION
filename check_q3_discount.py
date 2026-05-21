#!/usr/bin/env python
import requests
import re

url = "http://127.0.0.1:5000/quotation/3/print"
response = requests.get(url)

# Look for the discount row
if "値引き" in response.text:
    print("✅ '値引き' text found in page")
    # Extract the context
    idx = response.text.find("値引き")
    context = response.text[max(0, idx-200):idx+300]
    print(f"Context:\n{context}\n")
else:
    print("❌ '値引き' text NOT found in page")

# Look for -￥698,500
if "698,500" in response.text or "698500" in response.text:
    print("✅ Discount amount found in page")
else:
    print("❌ Discount amount NOT found in page")

# Find summary-table section
summary_match = re.search(r'<table class="summary-table">.*?</table>', response.text, re.DOTALL)
if summary_match:
    print("\nSummary table content:")
    print(summary_match.group(0)[:500])
