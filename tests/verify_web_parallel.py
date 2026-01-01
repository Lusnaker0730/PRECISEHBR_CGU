"""
Parallel Web Verification for PRECISE-HBR
-----------------------------------------
This script reads the Golden Dataset (CSV) and automatically verifies
the calculator results against the official website: https://precise-hbr.eoc.ch/

Requirements:
    pip install selenium webdriver-manager
"""
import csv
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Map dataset headers to Web Elements
# Using CSS selectors for stability. We'll identify numeric inputs by index if labels are tricky.
# Order observed: Age (0), Hb (1), WBC (2), eGFR (3)
SELECTORS = {
    'age_index': 0,
    'hb_index': 1,
    'wbc_index': 2,
    'egfr_index': 3,
    'prev_bleeding': "previousBleeding", # ID
    'anticoag': "longTermOralAnticoagulation", # ID
    # For ARC-HBR
    'arc_factor_example': "plateletCount", # ID
    'calculate_btn': "button[type='submit']", # CSS
}

def verify_parallel():
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'PreciseHBR_Golden_Dataset.csv')
    if not os.path.exists(csv_path):
        print(f"Error: Golden dataset not found at {csv_path}")
        return

    # Setup Browser
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Run headless by default for stability
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Attempt to use specific version matching the user's browser (133.0.6943.60) to avoid mismatch
    try:
        service = Service(ChromeDriverManager(driver_version="133.0.6943.60").install())
    except Exception:
        # Fallback to latest if specific fails
        print("Warning: Failed to install specific driver version, trying latest...")
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://precise-hbr.eoc.ch/")
    
    results = []
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            cases = list(reader)
            print(f"Starting verification of {len(cases)} cases against https://precise-hbr.eoc.ch/ ...")
            
            for i, case in enumerate(cases):
                # 1. Reset / Clear Form (simple way: refersh or clear fields. Refresh is safer)
                driver.refresh()
                # Wait for any numeric input
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']")))
                
                # Get all numeric inputs
                num_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
                
                if len(num_inputs) < 4:
                    print(f"Error: Found only {len(num_inputs)} numeric inputs, expected at least 4")
                    continue
                
                # 2. Input Data
                num_inputs[SELECTORS['age_index']].send_keys(case['age'])
                num_inputs[SELECTORS['hb_index']].send_keys(case['hb'])
                num_inputs[SELECTORS['wbc_index']].send_keys(case['wbc'])
                num_inputs[SELECTORS['egfr_index']].send_keys(case['egfr'])
                
                if case['bleeding'].lower() == 'true':
                    driver.find_element(By.ID, SELECTORS['prev_bleeding']).click()
                    
                if case['anticoag'].lower() == 'true':
                    driver.find_element(By.ID, SELECTORS['anticoag']).click()
                    
                if case['arc'].lower() == 'true':
                    # Select one ARC factor to trigger the +3 condition
                    driver.find_element(By.ID, SELECTORS['arc_factor_example']).click()
                
                # 3. Calculate
                calc_btn = driver.find_element(By.CSS_SELECTOR, SELECTORS['calculate_btn'])
                driver.execute_script("arguments[0].scrollIntoView();", calc_btn)
                # Wait for button to be enabled (sometimes form validation delay)
                time.sleep(0.5) 
                calc_btn.click()
                
                # 4. Extract Result
                # We wait for the result to appear.
                time.sleep(2.0) # Wait for JS (increased)
                
                # Naive text search if selector unknown
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Parse Score from text (Look for "Score" followed by digits)
                import re
                
                expected = int(float(case['expected_score'])) # CSV might be float string
                
                # Find "PRECISE-HBR Score: X" or similar
                # We look for digits that match our expected score to confirm presence, 
                # or just parse the first reasonable number after "Score"
                
                match = re.search(r'Score\s*[:=]?\s*(\d+(\.\d+)?)', body_text, re.IGNORECASE)
                web_score = -1
                if match:
                    try:
                        web_score = int(float(match.group(1)))
                    except ValueError:
                        pass
                
                case_id = case['case_id']
                match_status = "PASS" if web_score == expected else "FAIL"
                print(f"[{i+1}/{len(cases)}] {case_id}: Expected={expected}, Web={web_score} -> {match_status}")
                
                if match_status == "FAIL":
                    print(f"    DEBUG: Inputs - Age:{case['age']} Hb:{case['hb']} WBC:{case['wbc']} eGFR:{case['egfr']} Bld:{case['bleeding']} AC:{case['anticoag']} ARC:{case['arc']}")
                    # print(f"    DEBUG PAGE TEXT SNAPSHOT: {body_text[:200]}...") # Optional: Debug
                
                results.append({
                    'case_id': case_id,
                    'expected': expected,
                    'web_score': web_score,
                    'status': match_status
                })
                
                # Limit to 5 cases for demo if list is long (user can remove limit)
                if i >= 4: 
                    print("... Stopping after 5 cases for demonstration ...")
                    break

    finally:
        driver.quit()

if __name__ == "__main__":
    verify_parallel()
