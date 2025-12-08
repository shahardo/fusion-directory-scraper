"""
Fusion Energy Base Supply Chain Scraper
Scrapes company information from categorized pages using Selenium for JavaScript-rendered content
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import csv
import time
import sys
from typing import List, Dict, Optional
import re


class FusionDirectoryScraper:
    def __init__(self, base_url: str = "https://www.fusionenergybase.com", headless: bool = False, just_gather_categories: bool = False):
        self.base_url = base_url
        self.companies = []
        self.errors = []
        self.headless = headless
        self.just_gather_categories = just_gather_categories
        self.driver = None
        self.categories = []  # Store unique category/subcategory pairs
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp and level"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        sys.stdout.flush()
        
    def setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            self.log("Setting up Chrome WebDriver...")
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            self.log("WebDriver setup complete")
        except Exception as e:
            self.log(f"Failed to setup WebDriver: {str(e)}", "ERROR")
            raise
            
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.log("WebDriver closed")
            except:
                pass
                
    def wait_for_page_load(self, timeout: int = 30):
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            # Additional wait for React to render
            time.sleep(3)
        except TimeoutException:
            self.log("Page load timeout", "WARNING")
            
    def get_page_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Navigate to URL and return BeautifulSoup object"""
        try:
            self.log(f"Navigating to: {url}")
            self.driver.get(url)
            self.wait_for_page_load()
            
            # Get page source after JavaScript execution
            page_source = self.driver.page_source
            return BeautifulSoup(page_source, 'html.parser')
        except Exception as e:
            self.log(f"Error loading page {url}: {str(e)}", "ERROR")
            self.errors.append({"url": url, "error": str(e)})
            return None
            
    def extract_company_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract company links with their categories from the main page"""
        company_links = []
        
        self.log("Analyzing page structure to find company links with categories...")
        
        try:
            # Wait for content to fully load
            time.sleep(5)
            
            # Use Selenium to traverse the DOM and track categories/subcategories
            # Find all headings that might be categories or subcategories
            headings = self.driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6")
            
            # Build a map of element positions to track hierarchy
            # We'll use JavaScript to get the DOM structure
            script = """
            var result = [];
            // Collect relevant nodes in DOM order: category (.h2-responsive), subcategory (.h2-bold), and org links
            var ordered = [];
            var all = document.querySelectorAll('.h2-responsive, .h2-bold, a[href*="/organizations/"]');
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                if (el.matches('.h2-responsive')) {
                    ordered.push({ type: 'category', text: el.textContent.trim(), el: el });
                } else if (el.matches('.h2-bold')) {
                    ordered.push({ type: 'subcategory', text: el.textContent.trim(), el: el });
                } else {
                    ordered.push({ type: 'link', href: el.getAttribute('href'), text: el.textContent.trim(), el: el });
                }
            }
            // For each link, backtrack to nearest preceding subcategory (.h2-bold) and category (.h2-responsive)
            for (var i = 0; i < ordered.length; i++) {
                var item = ordered[i];
                if (item.type === 'link' && item.href && item.href.includes('/organizations/') && item.text) {
                    var sub = 'Unknown';
                    var cat = 'Unknown';
                    // backtrack for subcategory first
                    for (var j = i - 1; j >= 0; j--) {
                        var prev = ordered[j];
                        if (prev.type === 'subcategory') { sub = prev.text; break; }
                        if (prev.type === 'category' && cat === 'Unknown') { cat = prev.text; }
                    }
                    // ensure category is set to nearest previous .h2-responsive
                    if (cat === 'Unknown') {
                        for (var k = i - 1; k >= 0; k--) {
                            var prev2 = ordered[k];
                            if (prev2.type === 'category') { cat = prev2.text; break; }
                        }
                    }
                    result.push({ type: 'link', href: item.href, text: item.text, category: cat, subcategory: sub });
                }
            }
            return result;
            """
            
            elements = self.driver.execute_script(script)
            
            self.log(f"Found {len([e for e in elements if e.get('type') == 'heading'])} headings")
            self.log(f"Found {len([e for e in elements if e.get('type') == 'link'])} organization links")
            
            # Process the results
            current_category = "Unknown"
            current_subcategory = "Unknown"
            
            for elem in elements:
                if elem.get('type') == 'heading':
                    heading_text = elem.get('text', '').strip()
                    heading_level = elem.get('tag', '').upper()
                    
                    # Update current category/subcategory based on heading level
                    if heading_level in ['H1', 'H2']:
                        current_category = heading_text
                        current_subcategory = "Unknown"
                    elif heading_level in ['H3', 'H4']:
                        current_subcategory = heading_text
                
                elif elem.get('type') == 'link':
                    href = elem.get('href', '')
                    text = elem.get('text', '').strip()
                    category = elem.get('category', current_category)
                    subcategory = elem.get('subcategory', current_subcategory)
                    
                    # Build full URL
                    if href.startswith('/'):
                        full_url = self.base_url + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # Only include organization links
                    if '/organizations/' in full_url and text:
                        company_links.append({
                            'url': full_url,
                            'category': category,
                            'subcategory': subcategory,
                            'link_text': text
                        })
            
        except Exception as e:
            self.log(f"Error extracting links with categories: {str(e)}", "WARNING")
            import traceback
            traceback.print_exc()
            
            # Fallback: just get links without categories
            try:
                link_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/organizations/']")
                for link_elem in link_elements:
                    try:
                        href = link_elem.get_attribute('href')
                        text = link_elem.text.strip()
                        if href and text:
                            company_links.append({
                                'url': href,
                                'category': "Unknown",
                                'subcategory': "Unknown",
                                'link_text': text
                            })
                    except:
                        continue
            except:
                pass
        
        # Remove duplicates
        seen_urls = set()
        unique_links = []
        for link in company_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        self.log(f"Found {len(unique_links)} unique company links")
        return unique_links
        
    def extract_company_info(self, url: str, category: str, subcategory: str) -> Optional[Dict]:
        """Extract company information from a company page"""
        soup = self.get_page_soup(url)
        if not soup:
            return None
            
        company_info = {
            'category': category,
            'subcategory': subcategory,
            'company_name': '',
            'description': '',
            'city': '',
            'state': '',
            'url': url
        }
        
        # Extract company name
        name_selectors = [
            soup.find('h1'),
            soup.find('title'),
            soup.find(class_=lambda x: x and ('company' in str(x).lower() or 'name' in str(x).lower() or 'title' in str(x).lower())),
        ]
        
        # Also try Selenium
        try:
            h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
            if h1_elements:
                company_info['company_name'] = h1_elements[0].text.strip()
        except:
            pass
        
        if not company_info['company_name']:
            for selector in name_selectors:
                if selector:
                    name = selector.get_text(strip=True)
                    if name and len(name) > 2 and len(name) < 200:
                        # Clean up title tags
                        if '|' in name:
                            name = name.split('|')[0].strip()
                        company_info['company_name'] = name
                        break
        
        # Extract description
        desc_selectors = [
            soup.find('p', class_=lambda x: x and ('description' in str(x).lower() or 'about' in str(x).lower())),
            soup.find('div', class_=lambda x: x and ('description' in str(x).lower() or 'about' in str(x).lower())),
            soup.find('meta', attrs={'name': 'description'}),
        ]
        
        # Get first few paragraphs
        paragraphs = soup.find_all('p')
        for p in paragraphs[:5]:
            text = p.get_text(strip=True)
            if text and len(text) > 30 and len(text) < 1000:
                company_info['description'] = text[:500]
                break
        
        if not company_info['description']:
            for selector in desc_selectors:
                if selector:
                    if selector.name == 'meta':
                        company_info['description'] = selector.get('content', '')[:500]
                    else:
                        text = selector.get_text(strip=True)
                        if text and len(text) > 20:
                            company_info['description'] = text[:500]
                    if company_info['description']:
                        break
        
        # Extract location - look for "Location" heading and get the following content
        location_text = ''
        
        # Try to find "Location" heading using Selenium
        try:
            # Prefer headings that are exactly "Location" (case-insensitive)
            location_headers = self.driver.find_elements(
                By.XPATH,
                "//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6][normalize-space(translate(., 'LOCATION', 'location'))='location']"
            )
            # Fallback: any element whose text contains "Location"
            if not location_headers:
                location_headers = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(translate(text(), 'LOCATION', 'location'), 'location')]"
                )
            
            for header in location_headers:
                header_text = header.text.strip().lower()
                # Check if this is actually a "Location" heading (not just containing the word)
                if 'location' in header_text and len(header_text) < 50:
                    # Get the next sibling or parent's next sibling
                    try:
                        location_candidate = ''
                        # 1) Try the immediate following sibling block
                        try:
                            next_elem = header.find_element(By.XPATH, "following-sibling::*[1]")
                            location_candidate = next_elem.text.strip()
                        except Exception:
                            location_candidate = ''
                        # 2) If empty, try parent's text block (often header + content live together)
                        if not location_candidate:
                            try:
                                parent = header.find_element(By.XPATH, "..")
                                parent_text = parent.text.strip()
                                # Extract the first non-empty line AFTER the word "Location"
                                lines = [l.strip() for l in parent_text.splitlines() if l.strip()]
                                if 'location' in parent_text.lower():
                                    # Find index of the line that equals "Location" (case-insensitive)
                                    loc_idx = -1
                                    for i, line in enumerate(lines):
                                        if line.lower() == 'location':
                                            loc_idx = i
                                            break
                                    if loc_idx != -1 and loc_idx + 1 < len(lines):
                                        location_candidate = lines[loc_idx + 1]
                            except Exception:
                                pass
                        
                        # Extract location from the text (look for city, state pattern)
                        if location_candidate:
                            # Look for patterns like "City, State" or "City, ST"
                            location_patterns = [
                                r'Location[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b',
                                r'Location[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+)\b',
                                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b',
                                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+)\b',
                            ]
                            
                            for pattern in location_patterns:
                                matches = re.findall(pattern, location_candidate)
                                if matches:
                                    city, state = matches[0]
                                    us_states_2 = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
                                    us_state_map = {
                                        'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC','D.C.':'DC','Washington DC':'DC','Washington, DC':'DC'
                                    }
                                    if len(state) == 2 and state.upper() in us_states_2:
                                        company_info['city'] = city
                                        company_info['state'] = state.upper()
                                        location_text = f"{city}, {state}"
                                        break
                                    elif state in us_state_map:
                                        company_info['city'] = city
                                        company_info['state'] = us_state_map[state]
                                        location_text = f"{city}, {us_state_map[state]}"
                                        break
                            # If we still didn't parse, and the candidate is a single line like "City, Country",
                            # store city and country (country goes to 'state' per requirement)
                            if not location_text and ',' in location_candidate:
                                first, second = [p.strip() for p in location_candidate.split(',', 1)]
                                if first:
                                    company_info['city'] = first
                                    # Normalize if US state; otherwise treat as country
                                    us_state_map = {
                                        'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC','D.C.':'DC','Washington DC':'DC','Washington, DC':'DC'
                                    }
                                    if len(second) == 2 and second.upper() in us_state_map.values():
                                        company_info['state'] = second.upper()
                                    elif second in us_state_map:
                                        company_info['state'] = us_state_map[second]
                                    else:
                                        company_info['state'] = second  # country
                                    location_text = location_candidate
                            
                            if location_text:
                                break
                    except Exception as e:
                        continue
        except Exception as e:
            self.log(f"  Error finding location header: {str(e)}", "DEBUG")
        
        # If still no location, try BeautifulSoup approach
        if not location_text:
            try:
                # Find "Location" in the page
                page_text = soup.get_text()
                location_index = page_text.lower().find('location')
                if location_index != -1:
                    # Get text after "Location"
                    location_section = page_text[location_index:location_index+200]
                    # Look for city, state pattern
                    patterns = [
                        r'Location[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b',
                        r'Location[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+)\b',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, location_section)
                        if matches:
                            city, state = matches[0]
                            us_states_2 = set(['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'])
                            us_state_map = {
                                'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC','D.C.':'DC','Washington DC':'DC','Washington, DC':'DC'
                            }
                            if len(state) == 2 and state.upper() in us_states_2:
                                company_info['city'] = city
                                company_info['state'] = state.upper()
                                break
                            elif state in us_state_map:
                                company_info['city'] = city
                                company_info['state'] = us_state_map[state]
                                break
                            else:
                                # treat as country
                                company_info['city'] = city
                                company_info['state'] = state
                                break
            except:
                pass
        
        return company_info
        
    def scrape(self):
        """Main scraping function"""
        self.log("Starting Fusion Energy Base Supply Chain scraper")
        
        try:
            self.setup_driver()
        except Exception as e:
            self.log(f"Failed to initialize scraper: {str(e)}", "ERROR")
            return
        
        try:
            # Step 1: Get the main supply chain page
            main_url = f"{self.base_url}/supply-chain"
            self.log(f"Loading main page: {main_url}")
            main_soup = self.get_page_soup(main_url)
            
            if not main_soup:
                self.log("Failed to load main page. Aborting.", "ERROR")
                return
            
            # Save page source for debugging
            import os
            os.makedirs('output', exist_ok=True)
            with open('output/debug_main_page.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self.log("Page source saved to output/debug_main_page.html for inspection")
            
            # Step 2: Extract company links
            self.log("Extracting company links...")
            company_links = self.extract_company_links(main_soup)
            self.log(f"Found {len(company_links)} company links to process")
            
            if not company_links:
                self.log("No company links found. The page structure might be different than expected.", "WARNING")
                self.log("Please check output/debug_main_page.html to inspect the page structure.")
                return
            
            # Step 3: Gather categories and subcategories
            self.log("Gathering categories and subcategories...")
            seen_pairs = set()
            for link_info in company_links:
                category = link_info['category']
                subcategory = link_info['subcategory']
                pair = (category, subcategory)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    self.categories.append({
                        'category': category,
                        'subcategory': subcategory
                    })
            
            self.log(f"Found {len(self.categories)} unique category/subcategory pairs")
            
            # Always save categories CSV first
            scraper.display_categories()
            self.save_categories_to_csv()
            
            # If just gathering categories, skip company scraping
            if self.just_gather_categories:
                self.log("\n" + "="*80)
                self.log("Category gathering complete!")
                self.log(f"Found {len(self.categories)} unique category/subcategory pairs")
                return
            
            # Step 4: Visit each company page
            total = len(company_links)
            self.log(f"\nStarting to scrape {total} company pages...")
            self.log("="*80)
            
            for idx, link_info in enumerate(company_links, 1):
                url = link_info['url']
                category = link_info['category']
                subcategory = link_info['subcategory']
                
                self.log(f"\n[{idx}/{total}] Processing: {url}")
                self.log(f"  Category: {category}, Subcategory: {subcategory}")
                
                company_info = self.extract_company_info(url, category, subcategory)
                
                if company_info:
                    self.companies.append(company_info)
                    name = company_info['company_name'] or 'Unknown'
                    self.log(f"  ✓ Successfully extracted: {name}")
                    self.log(f"    Location: {company_info['city']}, {company_info['state']}")
                else:
                    self.log(f"  ✗ Failed to extract information", "WARNING")
                
                # Be respectful - add a delay between requests
                time.sleep(2)
            
            self.log("\n" + "="*80)
            self.log(f"Scraping complete!")
            self.log(f"Successfully scraped: {len(self.companies)} companies")
            self.log(f"Errors encountered: {len(self.errors)}")
            
        finally:
            self.close_driver()
        
    def save_to_csv(self, filename: str = "output/fusion_companies.csv"):
        """Save the scraped data to a CSV file"""
        if not self.companies:
            self.log("No companies to save.", "WARNING")
            return
        
        import os
        os.makedirs('output', exist_ok=True)
        self.log(f"Saving data to {filename}...")
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'subcategory', 'company_name', 'description', 'city', 'state', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for company in self.companies:
                writer.writerow(company)
        
        self.log(f"Data saved to {filename}")
        
    def save_categories_to_csv(self, filename: str = "output/fusion_categories.csv"):
        """Save the categories and subcategories to a CSV file"""
        if not self.categories:
            self.log("No categories to save.", "WARNING")
            return
        
        import os
        os.makedirs('output', exist_ok=True)
        self.log(f"Saving categories to {filename}...")
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'subcategory']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for cat_info in sorted(self.categories, key=lambda x: (x['category'], x['subcategory'])):
                writer.writerow(cat_info)
        
        self.log(f"Categories saved to {filename}")
        
    def display_categories(self):
        """Display the categories and subcategories"""
        print("\n" + "="*80)
        print("CATEGORIES AND SUBCATEGORIES")
        print("="*80)
        
        if not self.categories:
            print("No categories were found.")
            return
        
        # Group by category
        from collections import defaultdict
        category_map = defaultdict(list)
        for cat_info in self.categories:
            category_map[cat_info['category']].append(cat_info['subcategory'])
        
        for category in sorted(category_map.keys()):
            print(f"\n{category}")
            for subcategory in sorted(set(category_map[category])):
                print(f"  └─ {subcategory}")
        
        print("\n" + "="*80)
        print(f"Total: {len(category_map)} categories, {len(self.categories)} category/subcategory pairs")
        print("="*80)
        
    def display_results(self):
        """Display the scraped results"""
        print("\n" + "="*80)
        print("SCRAPED COMPANIES")
        print("="*80)
        
        if not self.companies:
            print("No companies were scraped.")
            return
        
        for idx, company in enumerate(self.companies, 1):
            print(f"\n[{idx}] {company['company_name'] or 'Unknown Company'}")
            print(f"    Category: {company['category']}")
            print(f"    Subcategory: {company['subcategory']}")
            print(f"    Location: {company['city']}, {company['state']}")
            desc = company['description']
            if desc:
                print(f"    Description: {desc[:100]}..." if len(desc) > 100 else f"    Description: {desc}")
            print(f"    URL: {company['url']}")
        
        print("\n" + "="*80)
        print(f"Total: {len(self.companies)} companies")
        print("="*80)
        
        if self.errors:
            print("\nERRORS ENCOUNTERED:")
            print("-"*80)
            for error in self.errors:
                print(f"  URL: {error['url']}")
                print(f"  Error: {error['error']}")
                print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape Fusion Energy Base Supply Chain directory')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--just-gather-categories', action='store_true', help='Only gather categories and subcategories, do not scrape companies')
    args = parser.parse_args()
    
    scraper = FusionDirectoryScraper(headless=args.headless, just_gather_categories=args.just_gather_categories)
    try:
        scraper.scrape()
        if not args.just_gather_categories:
            scraper.display_results()
            scraper.save_to_csv()
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        # Categories are already saved, only save companies if we were scraping them
        if not args.just_gather_categories:
            scraper.save_to_csv()  # Save what we have
        scraper.close_driver()
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Categories are already saved, only save companies if we were scraping them
        if not args.just_gather_categories:
            scraper.save_to_csv()  # Save what we have
        scraper.close_driver()
