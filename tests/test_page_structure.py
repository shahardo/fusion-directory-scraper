"""
Quick test to see the actual page structure when rendered
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

url = "https://www.fusionenergybase.com/supply-chain"

print("Setting up Chrome...")
chrome_options = Options()
# Don't run headless so we can see what's happening
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading: {url}")
    driver.get(url)
    
    # Wait for page to load
    print("Waiting for page to load...")
    time.sleep(10)  # Give it plenty of time
    
    # Save the rendered HTML
    import os
    os.makedirs('output', exist_ok=True)
    with open('output/rendered_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("Rendered HTML saved to output/rendered_page.html")
    
    # Try to find links
    links = driver.find_elements(By.TAG_NAME, "a")
    print(f"\nFound {len(links)} links")
    
    # Show first 30 links
    print("\nFirst 30 links:")
    for i, link in enumerate(links[:30], 1):
        try:
            href = link.get_attribute('href')
            text = link.text.strip()
            if href and text:
                print(f"{i}. {text[:60]:<60} -> {href[:80]}")
        except:
            pass
    
    # Look for specific elements
    print("\n\nLooking for category/subcategory elements...")
    
    # Check for headings
    headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4")
    print(f"Found {len(headings)} headings:")
    for h in headings[:10]:
        try:
            print(f"  - {h.tag_name}: {h.text[:100]}")
        except:
            pass
    
    # Check for divs with specific classes
    divs = driver.find_elements(By.CSS_SELECTOR, "[class*='category'], [class*='company'], [class*='supply']")
    print(f"\nFound {len(divs)} divs with category/company/supply in class")
    
    input("\nPress Enter to close browser...")
    
finally:
    driver.quit()
    print("Browser closed")

