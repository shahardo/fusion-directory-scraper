"""
Inspect the page structure to understand categories and location format
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
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading: {url}")
    driver.get(url)
    time.sleep(10)
    
    # Look for category structure
    print("\n=== Looking for Categories ===")
    # Try different selectors
    headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
    print(f"Found {len(headings)} headings")
    for h in headings[:20]:
        try:
            text = h.text.strip()
            if text:
                print(f"  {h.tag_name}: {text[:100]}")
        except:
            pass
    
    # Check a sample company page for location
    print("\n=== Checking sample company page for location ===")
    sample_url = "https://www.fusionenergybase.com/organizations/freemelt"
    driver.get(sample_url)
    time.sleep(5)
    
    # Look for "location" text
    body_text = driver.find_element(By.TAG_NAME, "body").text
    if "location" in body_text.lower():
        print("Found 'location' text in page")
        # Find elements containing location
        location_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Location') or contains(text(), 'location')]")
        print(f"Found {len(location_elements)} elements with 'location' text")
        for elem in location_elements[:5]:
            try:
                print(f"  Element: {elem.tag_name}, Text: {elem.text[:200]}")
                # Get parent and siblings
                parent = elem.find_element(By.XPATH, "..")
                print(f"    Parent text: {parent.text[:200]}")
            except:
                pass
    
    input("\nPress Enter to close...")
finally:
    driver.quit()

