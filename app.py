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
# ຟັງຊັນຄຳນວນ FCS ຕາມສູດ V13.8 (ດັດແປງຈາກຄັ້ງກ່ອນ)
# ------------------------------------------------------------
def calculate_fcs(match_data):
    # match_data ຕ້ອງມີ keys ຕາມນີ້
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
    
    # DR ຕາມລີກ (ສາມາດເພີ່ມໄດ້)
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
    
    # OA
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
# ຟັງຊັນດຶງຂໍ້ມູນຈາກ 7mth live ໂດຍໃຊ້ Selenium
# ------------------------------------------------------------
def scrape_7mth_live(url, headless=True, timeout=20):
    """
    ເປີດ URL ຂອງ 7mth (ຕົວຢ່າງ: https://freelive.7mth.com/live.aspx?mark=th&TimeZone=%2B0700)
    ດຶງຕາຕະລາງຫຼັງຈາກ JavaScript ໂຫຼດສຳເລັດ
    ຄືນ DataFrame ຂອງຂໍ້ມູນດິບ (ອາດມີຫຼາຍຕາຕະລາງ, ເລືອກເອົາຕາຕະລາງຫຼັກ)
    """
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    # ລໍຖ້າໃຫ້ຕາຕະລາງທີ່ມີຂໍ້ມູນປາກົດ (ປັບ selector ຕາມຄວາມເໝາະສົມ)
    try:
        # ລອງຫາຕາຕະລາງທີ່ມີ id ຫຼື class ທີ່ກ່ຽວຂ້ອງ
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.live-table, table#live_Table, table[class*='live']"))
        )
    except Exception as e:
        print(f"⚠️ ລໍຖ້າຕາຕະລາງບໍ່ສຳເລັດ: {e}")
    
    # ລໍຖ້າເພີ່ມອີກ 2 ວິນາທີເພື່ອໃຫ້ JavaScript ອັບເດດສຳເລັດ
    time.sleep(2)
    
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # ຄົ້ນຫາຕາຕະລາງທີ່ມີຂໍ້ມູນນັດ (ອາດມີຫຼາຍຕາຕະລາງ)
    # ຈາກ source code 7mth, ຕາຕະລາງຫຼັກມັກມີ id="live_Table"
    table = soup.find('table', id='live_Table')
    if not table:
        table = soup.find('table', class_='live-table')
    if not table:
        tables = soup.find_all('table')
        # ເລືອກເອົາຕາຕະລາງທີ່ມີຈຳນວນແຖວຫຼາຍທີ່ສຸດ
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
        else:
            raise Exception("ບໍ່ພົບຕາຕະລາງໃນໜ້າເວັບ")
    
    # ອ່ານຕາຕະລາງດ້ວຍ pandas
    df = pd.read_html(str(table))[0]
    return df, soup

# ------------------------------------------------------------
# ຟັງຊັນແປງ DataFrame ຈາກ 7mth ໃຫ້ເປັນຮູບແບບທີ່ calculate_fcs ຕ້ອງການ
# ------------------------------------------------------------
def parse_7mth_row_to_match(row_dict, league_name, is_home_favorite_from_handicap=True):
    """
    row_dict: dict ຂອງຂໍ້ມູນແຖວນັດ (ຈາກ DataFrame)
    ຟັງຊັນນີ້ຕ້ອງປັບໃຫ້ກົງກັບໂຄງສ້າງຂອງຕາຕະລາງຈິງ
    """
    # ຕົວຢ່າງການແປງ (ທ່ານຕ້ອງປັບຕາມຊື່ຄໍລຳທີ່ປາກົດຈິງ)
    # ສົມມຸດວ່າມີຄໍລຳ: ['Time', 'Home', 'Score', 'Away', 'H', 'A', 'Hdp', 'O1', 'O2']
    home_team = row_dict.get('Home', '')
    away_team = row_dict.get('Away', '')
    score = row_dict.get('Score', '0-0')
    handicap = row_dict.get('Hdp', '0')
    
    # ກຳນົດທີມຕໍ່ຈາກ Handicap (ເຄື່ອງໝາຍ - ໝາຍເຖິງທີມເຈົ້າບ້ານຕໍ່)
    if is_home_favorite_from_handicap:
        if isinstance(handicap, str) and '-' in handicap:
            is_home_favorite = True
        else:
            is_home_favorite = False
    else:
        # ຖ້າມີຄໍລຳແຍກບອກທີມຕໍ່ (ເຊັ່ນ 'Fav')
        is_home_favorite = row_dict.get('Fav', 'H') == 'H'
    
    # ອັນດັບ (ຕ້ອງດຶງຈາກແຫຼ່ງອື່ນ ຫຼື ຄາດຄະເນ)
    home_rank = extract_rank_from_text(row_dict.get('HomeRank', '10'))
    away_rank = extract_rank_from_text(row_dict.get('AwayRank', '10'))
    
    # ຟອມ 5 ນັດຫຼ້າສຸດ (ຕ້ອງດຶງຈາກຄໍລຳສະເພາະ ຫຼື ຄິດໄລ່ຈາກປະຫວັດ)
    home_form = parse_form_string(row_dict.get('HomeForm', 'DDDDD'))
    away_form = parse_form_string(row_dict.get('AwayForm', 'DDDDD'))
    
    # ປະຕູເສລີ່ຍ (ຕ້ອງດຶງຈາກສະຖິຕິລີກ)
    home_gf = extract_goals_avg(row_dict.get('HomeGF', '1.0'))
    home_ga = extract_goals_avg(row_dict.get('HomeGA', '1.0'))
    away_gf = extract_goals_avg(row_dict.get('AwayGF', '1.0'))
    away_ga = extract_goals_avg(row_dict.get('AwayGA', '1.0'))
    
    # odds ເລີ່ມຕົ້ນຂອງທີມຕໍ່
    fav_odds = extract_odds(row_dict.get('FavOdds', '1.85'))
    
    # H2H (ຖ້າມີຂໍ້ມູນ, ຕ້ອງດຶງຈາກແຫຼ່ງອື່ນ)
    h2h_matches = []
    
    match = {
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
        'h2h_matches': h2h_matches,
        'is_home_favorite': is_home_favorite,
        'favorite_initial_odds': fav_odds,
        'error_count': 0
    }
    return match

def extract_rank_from_text(rank_str):
    try:
        return int(re.search(r'\d+', str(rank_str)).group())
    except:
        return 10

def parse_form_string(form_str):
    form_str = str(form_str).upper()
    return [ch for ch in form_str if ch in 'WDL']

def extract_goals_avg(goals_str):
    try:
        return float(re.search(r'[\d\.]+', str(goals_str)).group())
    except:
        return 1.0

def extract_odds(odds_str):
    try:
        return float(re.search(r'[\d\.]+', str(odds_str)).group())
    except:
        return 1.85

# ------------------------------------------------------------
# ຟັງຊັນຫຼັກ: ດຶງຂໍ້ມູນຈາກ 7mth ແລະ ວິເຄາະ
# ------------------------------------------------------------
def auto_analyze_from_7mth(url, league_name='Unknown', headless=True):
    print("📥 ກຳລັງເປີດໜ້າເວັບ ແລະ ດຶງຂໍ້ມູນ...")
    df_raw, soup = scrape_7mth_live(url, headless=headless)
    print(f"✅ ດຶງຂໍ້ມູນສຳເລັດ: {len(df_raw)} ແຖວ")
    
    # ສະແດງຕົວຢ່າງຂໍ້ມູນເພື່ອໃຫ້ຜູ້ໃຊ້ປັບການແປງ
    print("\n📋 ຕົວຢ່າງ 5 ແຖວທຳອິດຂອງຂໍ້ມູນດິບ:")
    print(df_raw.head())
    print("\n📋 ຊື່ຄໍລຳທີ່ພົບ:")
    print(df_raw.columns.tolist())
    
    # ແປງແຕ່ລະແຖວເປັນ match dict (ຕ້ອງປັບຕາມໂຄງສ້າງຈິງ)
    matches = []
    for idx, row in df_raw.iterrows():
        try:
            match = parse_7mth_row_to_match(row.to_dict(), league_name)
            matches.append(match)
        except Exception as e:
            print(f"⚠️ ຂ້າມແຖວ {idx} ຍ້ອນຂໍ້ຜິດພາດ: {e}")
    
    # ຄຳນວນ FCS ແລະ ຕັດສິນໃຈ
    results = []
    for m in matches:
        fcs = calculate_fcs(m)
        decision = get_decision(fcs, m['league'])
        results.append({
            'ລີກ': m['league'],
            'ເຈົ້າບ້ານ': m['home_team'],
            'ທີມຢາມ': m['away_team'],
            'FCS': round(fcs, 2),
            'ຄຳແນະນຳ': decision
        })
    
    df_result = pd.DataFrame(results)
    return df_result

# ------------------------------------------------------------
# ຕົວຢ່າງການໃຊ້ງານ
# ------------------------------------------------------------
if __name__ == "__main__":
    # URL ຂອງ 7mth ພາສາທີ່ທ່ານຕ້ອງການ (ປ່ຽນ mark=th ເປັນ vn, en, kr ຕາມຕ້ອງການ)
    TARGET_URL = "https://freelive.7mth.com/live.aspx?mark=th&TimeZone=%2B0700"
    
    # ເອີ້ນໃຊ້ງານ
    result = auto_analyze_from_7mth(TARGET_URL, league_name='7mth Live')
    
    print("\n📊 **ຜົນການວິເຄາະອັດຕະໂນມັດ**")
    print(result.to_string(index=False))
    
    # ບັນທຶກ CSV
    result.to_csv("7mth_analysis_result.csv", index=False, encoding='utf-8-sig')
    print("\n💾 ບັນທຶກຜົນໄວ້ທີ່ 7mth_analysis_result.csv")
