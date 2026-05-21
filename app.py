import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# FCS Calculation (V13.8) – same as before
# ------------------------------------------------------------
def calculate_fcs(match_data):
    si = max(0.90, min(1.10, 0.90 + (abs(match_data['home_rank'] - match_data['away_rank']) * 0.02)))
    if match_data['is_home_favorite']:
        undefeated = sum(1 for r in match_data['home_form_5'][:5] if r in 'WD')
    else:
        undefeated = sum(1 for r in match_data['away_form_5'][:5] if r in 'WD')
    wm = max(0.80, min(1.20, 1.00 + ((undefeated/5.0 - 0.50) * 0.40)))
    fav_gf = match_data['home_gf'] if match_data['is_home_favorite'] else match_data['away_gf']
    fav_ga = match_data['home_ga'] if match_data['is_home_favorite'] else match_data['away_ga']
    und_gf = match_data['away_gf'] if match_data['is_home_favorite'] else match_data['home_gf']
    und_ga = match_data['away_ga'] if match_data['is_home_favorite'] else match_data['home_ga']
    fav_ratio = fav_gf / max(1.0, fav_ga)
    und_ratio = und_gf / max(1.0, und_ga)
    pp = max(0.90, min(1.10, 1.00 + ((fav_ratio - und_ratio) * 0.20)))
    if match_data.get('h2h_matches') and len(match_data['h2h_matches']) > 0:
        undefeated_h2h = 0
        for m in match_data['h2h_matches']:
            if match_data['is_home_favorite']:
                if m['home_score'] >= m['away_score']:
                    undefeated_h2h += 1
            else:
                if m['away_score'] >= m['home_score']:
                    undefeated_h2h += 1
        h2h_rate = undefeated_h2h / len(match_data['h2h_matches'])
        h2h = max(0.80, min(1.20, 0.80 + (h2h_rate * 0.40)))
    else:
        h2h = 1.00
    am = max(0.85, min(1.15, (si + wm + pp + h2h) / 4.0))
    dr_league_map = {
        'FIN D1': 0.85, 'NOR D1': 0.90, 'SWE D1': 0.90,
        'LIB Cup': 0.80, 'HON D1': 0.90, 'ARM D1': 0.90,
        'ITA D2': 0.95, 'ENG PR': 0.90, 'BEL D1': 0.90,
    }
    base_dr = dr_league_map.get(match_data.get('league', ''), 1.00)
    error_count = match_data.get('error_count', 0)
    dr = max(0.50, min(1.00, base_dr - (error_count * 0.05)))
    fcs_raw = si * wm * pp * h2h * am * dr
    fcs = fcs_raw * 100.0
    oa = (match_data.get('favorite_initial_odds', 1.85) - 1.85) / 0.10
    if oa > 1.5:
        fcs *= 1.05
    elif oa < -1.5:
        fcs *= 0.95
    return fcs

def get_decision(fcs, league):
    ranges = {
        'FIN D1': (200, 120), 'NOR D1': (120, 80), 'SWE D1': (120, 80),
        'LIB Cup': (100, 70), 'HON D1': (80, 55), 'ARM D1': (180, 120),
        'ITA D2': (160, 100), 'ENG PR': (115, 85), 'BEL D1': (80, 55),
    }
    if league in ranges:
        high, low = ranges[league]
        if fcs > high:
            return 'ຮອງ'
        elif fcs >= low:
            return 'ຕໍ່'
        else:
            return 'ຮອງ'
    else:
        if fcs > 150:
            return 'ຮອງ'
        elif fcs >= 55:
            return 'ຕໍ່'
        elif 45 <= fcs < 55:
            return '⚠️ ຫຼີກລ່ຽງ'
        else:
            return 'ຮອງ'

# ------------------------------------------------------------
# Scrape from iframe (updated)
# ------------------------------------------------------------
def scrape_7mth_live_with_iframe(headless=True, timeout=25):
    # This is the main page that contains the iframe
    main_url = "https://freelive.7mth2.com/live.aspx?mark=th&TimeZone=%2B0700&wordAd=&wadurl=//&width=700&cpageBgColor=FFFFFF&tableFontSize=11&cborderColor=DDDDDD&ctdColor1=FFFFFF&ctdColor2=E0E9F6&clinkColor=0044DD&cdateFontColor=333333&cdateBgColor=FFFFFF&scoreFontSize=12&cteamFontColor=000000&cgoalFontColor=FF0000&cgoalBgColor=FFFFE1&cremarkFontColor=0000FF&cremarkBgColor=F7F8F3&Skins=10&teamWeight=400&scoreWeight=700&goalWeight=400&fontWeight=700&DSTbox="
    
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    
    driver = webdriver.Chrome(options=options)
    driver.get(main_url)
    
    # Wait for iframe to be present
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        print("✅ Iframe found")
    except:
        print("⚠️ No iframe found – maybe table is directly on page")
    
    # Switch to the iframe (there is usually only one)
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        driver.switch_to.frame(iframes[0])
        print("🔁 Switched to iframe")
    else:
        print("⚠️ No iframe to switch, continuing with main page")
    
    # Wait for the live table inside the iframe
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "live_Table"))
        )
        print("✅ Found live_Table inside iframe")
    except:
        print("⚠️ live_Table not found, will search for any table")
    
    time.sleep(3)  # extra wait for dynamic JS updates
    
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='live_Table')
    if not table:
        table = soup.find('table', class_='live-table')
    if not table:
        tables = soup.find_all('table')
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
        else:
            raise Exception("No table found inside iframe")
    
    df = pd.read_html(str(table))[0]
    return df, soup

# ------------------------------------------------------------
# Parse raw DataFrame row to match dict (you MUST adjust this)
# ------------------------------------------------------------
def parse_row_to_match(row_dict, league_name="7mth"):
    """
    IMPORTANT: Run the script once, look at printed column names,
    then edit this function to use the correct column names.
    """
    # Example column names (Thai/English mix – change after inspection)
    home_team = row_dict.get('เจ้าบ้าน', row_dict.get('Home', ''))
    away_team = row_dict.get('ทีมเยือน', row_dict.get('Away', ''))
    handicap = row_dict.get('แต้มต่อ', row_dict.get('Hdp', '0'))
    
    # Determine favorite from handicap ( '-' means home favorite)
    is_home_favorite = '-' in str(handicap) if handicap else False
    
    # Placeholder values – you should fetch real data from detail pages
    home_rank = 10
    away_rank = 10
    home_form = ['D','D','D','D','D']
    away_form = ['D','D','D','D','D']
    home_gf = 1.2
    home_ga = 1.0
    away_gf = 1.2
    away_ga = 1.0
    fav_odds = 1.85
    
    return {
        'league': league_name,
        'home_team': home_team,
        'away_team': away_team,
        'home_rank': home_rank,
        'away_rank': away_rank,
        'home_form_5': home_form,
        'away_form_5': away_form,
        'home_gf': home_gf,
        'home_ga': home_ga,
        'away_gf': away_gf,
        'away_ga': away_ga,
        'h2h_matches': [],
        'is_home_favorite': is_home_favorite,
        'favorite_initial_odds': fav_odds,
        'error_count': 0
    }

# ------------------------------------------------------------
# Main automation
# ------------------------------------------------------------
def auto_analyze():
    print("📥 Loading 7mth live data (with iframe)...")
    df_raw, _ = scrape_7mth_live_with_iframe(headless=True)
    print(f"✅ Raw rows: {len(df_raw)}")
    
    print("\n📋 First 3 rows (to see structure):")
    print(df_raw.head(3))
    print("\n📋 Column names:")
    print(df_raw.columns.tolist())
    
    matches = []
    for idx, row in df_raw.iterrows():
        try:
            match = parse_row_to_match(row.to_dict())
            matches.append(match)
        except Exception as e:
            print(f"⚠️ Skip row {idx}: {e}")
    
    results = []
    for m in matches:
        fcs = calculate_fcs(m)
        decision = get_decision(fcs, m['league'])
        results.append({
            'League': m['league'],
            'Home': m['home_team'],
            'Away': m['away_team'],
            'FCS': round(fcs, 2),
            'Decision': decision
        })
    
    df_result = pd.DataFrame(results)
    return df_result

if __name__ == "__main__":
    df = auto_analyze()
    print("\n📊 Final Analysis (V13.8):")
    print(df.to_string(index=False))
    df.to_csv("7mth_iframe_analysis.csv", index=False, encoding='utf-8-sig')
    print("\n💾 Saved to 7mth_iframe_analysis.csv")
