"""
NHI Code Fetcher Tool
Fetches Taiwan NHI medication codes from the official NHIA website.
Target URL: https://info.nhi.gov.tw/INAE3000/INAE3000S02

Usage:
    python tools/nhi_code_fetcher.py "Warfarin"
    python tools/nhi_code_fetcher.py --update-config
"""
import requests
import json
import sys
import os
import time
import re
from bs4 import BeautifulSoup
import argparse

# Add parent directory to path to load config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from services.config_loader import config_loader
except ImportError:
    print("Warning: Could not import config_loader. Configuration update feature will be disabled.")
    config_loader = None

class NHICodeFetcher:
    BASE_URL = "https://info.nhi.gov.tw/INAE3000/INAE3000S02"
    QUERY_URL = "https://info.nhi.gov.tw/INAE3000/INAE3000S02/Query"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        })

    def search_drug(self, keyword):
        """
        Search for a drug by keyword (English name)
        Returns a list of dictionaries with code and name
        """
        print(f"Searching for: {keyword}...")
        
        # Note: This is a simulation based on common ASP.NET/MVC patterns used in government sites.
        # The actual parameters might need adjustment if the site changes.
        # Based on INAE3000S02, it likely uses a POST request with specific form data.
        
        # Since we cannot browse live to reverse engineer the exact payload,
        # this function attempts a standard query structure.
        # If this fails, the user might need to inspect the Network tab in DevTools
        # to get the exact payload structure.
        
        payload = {
            'Q_DrugName': keyword,
            'Q_DrugCode': '',
            'Action': 'Query'
        }
        
        try:
            # 1. First visit the page to get cookies/tokens if needed
            self.session.get(self.BASE_URL)
            
            # 2. Perform the query
            # Note: Government sites often return HTML fragments or specific JSON structures
            response = self.session.post(self.QUERY_URL, data=payload)
            
            if response.status_code != 200:
                print(f"Error: Server returned status {response.status_code}")
                return []
            
            return self._parse_response(response.text)
            
        except Exception as e:
            print(f"Connection error: {e}")
            return []

    def _parse_response(self, content):
        """
        Parse the response content. 
        Attempts to handle both JSON and HTML table responses.
        """
        results = []
        
        try:
            # Try parsing as JSON first
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    # Adjust keys based on actual API response
                    code = item.get('DrugCode') or item.get('Code')
                    name = item.get('DrugName') or item.get('Name')
                    if code:
                        results.append({'code': code, 'name': name})
                return results
        except json.JSONDecodeError:
            pass
            
        # Fallback to HTML parsing
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # Look for table rows
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Heuristic: Code is usually first or second column, 10-12 chars
                    text1 = cols[0].get_text(strip=True)
                    text2 = cols[1].get_text(strip=True)
                    
                    # Check if text1 looks like an NHI code (e.g., A023...)
                    if self._is_nhi_code(text1):
                        results.append({'code': text1, 'name': text2})
                    elif self._is_nhi_code(text2):
                        results.append({'code': text2, 'name': cols[2].get_text(strip=True) if len(cols)>2 else ""})
                        
        except Exception as e:
            print(f"Parsing error: {e}")
            
        return results

    def _is_nhi_code(self, text):
        """Basic validation for NHI code format"""
        if not text: return False
        # Standard format: 2 chars + digits, or 1 char + digits, usually 10-12 chars
        return len(text) >= 5 and (text[0].isalpha() or text[0].isdigit())

def update_config_file(keyword, new_codes):
    """Updates the cdss_config.json file with new codes"""
    if not config_loader:
        return
    
    config_path = 'cdss_config.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Locate the oral_anticoagulants or nsaids sections
        med_config = data.get('medication_keywords', {})
        
        target_section = None
        section_name = ""
        
        # Heuristic to determine which section to update based on keyword
        # This is a simple logic, can be improved
        keyword_lower = keyword.lower()
        
        if any(x in keyword_lower for x in ['warfarin', 'apixaban', 'rivaroxaban', 'dabigatran', 'edoxaban']):
            target_section = med_config.get('oral_anticoagulants')
            section_name = "Oral Anticoagulants"
        elif any(x in keyword_lower for x in ['aspirin', 'ibuprofen', 'naproxen', 'nsaid']):
            target_section = med_config.get('nsaids_corticosteroids')
            section_name = "NSAIDs/Corticosteroids"
            
        if target_section:
            current_codes = target_section.get('nhi_codes', [])
            # Merge unique codes
            updated_codes = sorted(list(set(current_codes + new_codes)))
            target_section['nhi_codes'] = updated_codes
            
            print(f"Updating {section_name} with {len(new_codes)} new codes...")
            print(f"Total codes: {len(updated_codes)}")
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("Config file updated successfully.")
        else:
            print("Could not automatically determine which category this drug belongs to.")
            print("Please manually add these codes to cdss_config.json")

    except Exception as e:
        print(f"Error updating config: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch NHI codes')
    parser.add_argument('keyword', nargs='?', help='Drug name to search')
    parser.add_argument('--auto-update', action='store_true', help='Automatically update known drug categories in config')
    
    args = parser.parse_args()
    
    if not args.keyword:
        # Demo mode if no keyword
        print("No keyword provided. Running demo search for 'Warfarin'...")
        args.keyword = "Warfarin"
    
    fetcher = NHICodeFetcher()
    results = fetcher.search_drug(args.keyword)
    
    if results:
        print(f"\nFound {len(results)} results for '{args.keyword}':")
        codes = []
        for item in results:
            print(f"  [{item['code']}] {item['name']}")
            codes.append(item['code'])
            
        if args.auto_update:
            update_config_file(args.keyword, codes)
        else:
            print("\nTo add these to your config, add this list to 'nhi_codes':")
            print(json.dumps(codes))
    else:
        print("No results found. The website might have changed its layout or parameters.")
        print("Please manually verify at: https://info.nhi.gov.tw/INAE3000/INAE3000S02")

