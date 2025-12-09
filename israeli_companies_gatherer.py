"""
Israeli Companies Gatherer
Uses Groq API to find Israeli companies for each fusion energy subcategory
"""

import csv
import json
import time
import sys
import re
import os
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class IsraeliCompaniesGatherer:
    def __init__(self):
        """
        Initialize the Israeli Companies Gatherer.
        
        The Groq client will automatically read the API key from the GROQ_API_KEY
        environment variable. Environment variables can be set via:
        - A .env file in the project root (loaded automatically)
        - System environment variables
        """
        # Groq client automatically reads from GROQ_API_KEY environment variable
        # which is now loaded from .env file via load_dotenv() at module level
        self.client = Groq()
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp and level"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        sys.stdout.flush()
    
    def query_groq_for_israeli_companies(self, subcategory: str) -> List[Dict]:
        """Query Groq API to find Israeli companies for a given subcategory"""
        # Construct the Hebrew prompt with the subcategory
        prompt = f"בצע חיפוש עומק, לחברות ישראליות שעוסקות בתחום {subcategory}, חפש גם באנגלית וגם בעברית. שים דגש על חברות המייצרות ומפתחות רכיבים חדשניים בתחום, ולא על חברות המייבאות רכיבים. סכם את הממצאים בטבלת JSON עם השדות: companyName, website, headquarters, yearFounded, coreProducts, innovations, notes"
        
        self.log(f"Querying Groq for Israeli companies in subcategory: {subcategory}")
        
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=1,
                max_completion_tokens=8192,
                top_p=1,
                reasoning_effort="medium",
                stream=True,
                stop=None,
                tools=[{"type": "browser_search"}]
            )
            
            # Collect the streaming response
            full_response = ""
            for chunk in completion:
                content = chunk.choices[0].delta.content or ""
                full_response += content
                print(content, end="")
            
            print()  # New line after streaming
            
            # Try to parse JSON from the response
            # Look for JSON array or object in the response
            companies = []
            
            # Try to extract JSON from the response
            # The response might contain markdown code blocks with JSON
            json_start = full_response.find('[')
            json_end = full_response.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = full_response[json_start:json_end]
                try:
                    companies_data = json.loads(json_str)
                    if isinstance(companies_data, list):
                        for company in companies_data:
                            if isinstance(company, dict):
                                companies.append({
                                    'companyName': company.get('companyName', ''),
                                    'website': company.get('website', ''),
                                    'headquarters': company.get('headquarters', ''),
                                    'yearFounded': company.get('yearFounded', ''),
                                    'coreProducts': company.get('coreProducts', ''),
                                    'innovations': company.get('innovations', ''),
                                    'notes': company.get('notes', '')
                                })
                    elif isinstance(companies_data, dict):
                        # Single company object
                        companies.append({
                            'companyName': companies_data.get('companyName', ''),
                            'website': companies_data.get('website', ''),
                            'headquarters': companies_data.get('headquarters', ''),
                            'yearFounded': companies_data.get('yearFounded', ''),
                            'coreProducts': companies_data.get('coreProducts', ''),
                            'innovations': companies_data.get('innovations', ''),
                            'notes': companies_data.get('notes', '')
                        })
                except json.JSONDecodeError as e:
                    self.log(f"Failed to parse JSON from response: {str(e)}", "WARNING")
                    self.log(f"Response content: {full_response[:500]}...", "DEBUG")
            else:
                # Try to find JSON in code blocks
                json_pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
                matches = re.findall(json_pattern, full_response, re.DOTALL)
                if matches:
                    try:
                        companies_data = json.loads(matches[0])
                        if isinstance(companies_data, list):
                            companies = companies_data
                    except json.JSONDecodeError:
                        pass
            
            self.log(f"Found {len(companies)} Israeli companies for {subcategory}")
            return companies
            
        except Exception as e:
            self.log(f"Error querying Groq for {subcategory}: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            return []
    
    def load_categories_from_csv(self, filename: str = "output/fusion_categories.csv") -> List[Dict]:
        """Load categories and subcategories from CSV file"""
        categories = []
        try:
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    categories.append({
                        'category': row['category'],
                        'subcategory': row['subcategory']
                    })
            self.log(f"Loaded {len(categories)} category/subcategory pairs from {filename}")
        except FileNotFoundError:
            self.log(f"Categories file not found: {filename}", "ERROR")
        except Exception as e:
            self.log(f"Error loading categories from CSV: {str(e)}", "ERROR")
        return categories
    
    def gather_israeli_companies_for_all_subcategories(self, categories_file: str = "output/fusion_categories.csv", limit: int = None) -> List[Dict]:
        """Gather Israeli companies for all subcategories using Groq API"""
        self.log("Starting to gather Israeli companies for all subcategories")
        if limit is not None:
            self.log(f"Limited to first {limit} subcategories")
        self.log("="*80)
        
        # Load categories from CSV
        categories = self.load_categories_from_csv(categories_file)
        
        if not categories:
            self.log("No categories found. Please run the scraper first to generate categories.", "ERROR")
            return []
        
        # Apply limit if specified
        if limit is not None:
            categories = categories[:limit]
            self.log(f"Processing limited to first {limit} subcategories")
        
        # Store all Israeli companies with their category/subcategory info
        israeli_companies = []
        
        total = len(categories)
        self.log(f"Processing {total} subcategories...")
        
        for idx, cat_info in enumerate(categories, 1):
            category = cat_info['category']
            subcategory = cat_info['subcategory']
            
            self.log(f"\n[{idx}/{total}] Processing: {category} > {subcategory}")
            self.log("-" * 80)
            
            # Query Groq for Israeli companies in this subcategory
            companies = self.query_groq_for_israeli_companies(subcategory)
            
            # Add category and subcategory to each company
            for company in companies:
                company['category'] = category
                company['subcategory'] = subcategory
                israeli_companies.append(company)
            
            # Be respectful - add a delay between API calls
            if idx < total:
                time.sleep(2)
        
        self.log("\n" + "="*80)
        self.log(f"Gathering complete!")
        self.log(f"Found {len(israeli_companies)} Israeli companies across {total} subcategories")
        
        return israeli_companies
    
    def save_israeli_companies_to_csv(self, companies: List[Dict], filename: str = "output/israeli_companies.csv"):
        """Save Israeli companies data to CSV file"""
        if not companies:
            self.log("No Israeli companies to save.", "WARNING")
            return
        
        os.makedirs('output', exist_ok=True)
        self.log(f"Saving Israeli companies data to {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'subcategory', 'companyName', 'website', 'headquarters', 
                         'yearFounded', 'coreProducts', 'innovations', 'notes']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for company in companies:
                writer.writerow(company)
        
        self.log(f"Israeli companies data saved to {filename}")


if __name__ == "__main__":
    """Standalone script to gather Israeli companies"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gather Israeli companies for fusion energy subcategories using Groq API')
    parser.add_argument('--categories-file', default='output/fusion_categories.csv', 
                       help='Path to categories CSV file (default: output/fusion_categories.csv)')
    parser.add_argument('--output-file', default='output/israeli_companies.csv',
                       help='Path to output CSV file (default: output/israeli_companies.csv)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit processing to first n subcategories')
    args = parser.parse_args()
    
    gatherer = IsraeliCompaniesGatherer()
    
    try:
        israeli_companies = gatherer.gather_israeli_companies_for_all_subcategories(args.categories_file, limit=args.limit)
        gatherer.save_israeli_companies_to_csv(israeli_companies, args.output_file)
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()

