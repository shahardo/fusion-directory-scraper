"""
Quick script to inspect the page structure
"""
import requests
from bs4 import BeautifulSoup

url = "https://www.fusionenergybase.com/supply-chain"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=30)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.content, 'html.parser')

# Save the HTML for inspection
import os
os.makedirs('output', exist_ok=True)
with open('output/page_structure.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print("Page saved to output/page_structure.html")

# Look for links
links = soup.find_all('a', href=True)
print(f"\nFound {len(links)} links")

# Show first 20 links
print("\nFirst 20 links:")
for i, link in enumerate(links[:20], 1):
    href = link.get('href', '')
    text = link.get_text(strip=True)
    print(f"{i}. {text[:50]:<50} -> {href[:80]}")

# Look for category/subcategory patterns
print("\n\nLooking for category patterns...")
for tag in ['h1', 'h2', 'h3', 'h4', 'section', 'div']:
    elements = soup.find_all(tag)
    if elements:
        print(f"\n{tag.upper()} tags found: {len(elements)}")
        for elem in elements[:5]:
            classes = elem.get('class', [])
            text = elem.get_text(strip=True)[:100]
            if text:
                print(f"  Class: {classes}, Text: {text}")

