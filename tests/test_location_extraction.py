"""
Test script to see how location is structured on a company page
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

url = "https://www.fusionenergybase.com/organizations/freemelt"

print("Setting up Chrome...")
chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading: {url}")
    driver.get(url)
    time.sleep(5)
    
    # Get all text
    body_text = driver.find_element(By.TAG_NAME, "body").text
    print("\n=== Searching for 'Location' in page text ===")
    location_index = body_text.lower().find('location')
    if location_index != -1:
        print(f"Found 'location' at index {location_index}")
        print(f"Context: {body_text[location_index-50:location_index+200]}")
    else:
        print("'location' not found in page text")
    
    # Try to find elements with location
    print("\n=== Looking for elements containing 'Location' ===")
    try:
        location_elements = driver.find_elements(By.XPATH, 
            "//*[contains(translate(text(), 'LOCATION', 'location'), 'location')]")
        print(f"Found {len(location_elements)} elements with 'location'")
        for i, elem in enumerate(location_elements[:5], 1):
            print(f"\n{i}. Tag: {elem.tag_name}")
            print(f"   Text: {elem.text[:200]}")
            try:
                parent = elem.find_element(By.XPATH, "..")
                print(f"   Parent text: {parent.text[:300]}")
            except:
                pass
    except Exception as e:
        print(f"Error: {e}")
    
    # Save page source
    import os
    os.makedirs('output', exist_ok=True)
    with open('output/test_company_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("\nPage source saved to output/test_company_page.html")
    
    input("\nPress Enter to close...")
finally:
    driver.quit()

