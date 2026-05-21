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
# ຟັງຊັນຄຳນວນ FCS ແລະ ຕັດສິນໃຈ (ຄືເກົ່າ, ຮັກສາໄວ້)
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
# ຟັງຊັນດຶງຂໍ້ມູນຈາກ URL ທີ່ກຳນົດ (ໂດຍສະເພາະ 7mth2)
# ------------------------------------------------------------
def scrape_7mth2_live(headless=True, timeout=25):
    """
    ດຶງຂໍ້ມູນສົດຈາກ freelive.7mth2.com ຕາມ URL ທີ່ທ່ານໃຫ້ມາ.
    ຄືນ DataFrame ຂອງຂໍ້ມູນດິບ ແລະ ເນື້ອໃນ HTML ທີ່ປຸງແຕ່ງແລ້ວ.
    """
    url = "https://freelive.7mth2.com/live.aspx?mark=th&TimeZone=%2B0700&wordAd=&wadurl=//&width=700&cpageBgColor=FFFFFF&tableFontSize=11&cborderColor=DDDDDD&ctdColor1=FFFFFF&ctdColor2=E0E9F6&clinkColor=0044DD&cdateFontColor=333333&cdateBgColor=FFFFFF&scoreFontSize=12&cteamFontColor=000000&cgoalFontColor=FF0000&cgoalBgColor=FFFFE1&cremarkFontColor=0000FF&cremarkBgColor=F7F8F3&Skins=10&teamWeight=400&scoreWeight=700&goalWeight=400&fontWeight=700&DSTbox="
    
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    # ລໍຖ້າໃຫ້ຕາຕະລາງທີ່ມີ id="live_Table" ປາກົດ (ກົງກັບ source code ຂອງ 7mth)
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "live_Table"))
        )
        print("✅ ພົບຕາຕະລາງ live_Table")
    except:
        print("⚠️ ບໍ່ພົບ live_Table, ລອງຊອກຫາຕາຕະລາງອື່ນ...")
    
    # ລໍຖ້າເພີ່ມເລັກນ້ອຍເພື່ອໃຫ້ JavaScript ສ້າງແຖວຂໍ້ມູນສຳເລັດ
    time.sleep(3)
    
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='live_Table')
    if not table:
        # ຫາຕາຕະລາງທີ່ມີຂໍ້ມູນນັດອາດຊື່ອື່ນ
        table = soup.find('table', class_='live-table')
    if not table:
        tables = soup.find_all('table')
        if tables:
            table = max(tables, key=lambda t: len(t.find_all('tr')))
        else:
            raise Exception("ບໍ່ພົບຕາຕະລາງໃນໜ້າເວັບ")
    
    df = pd.read_html(str(table))[0]
    return df, soup

# ------------------------------------------------------------
# ຟັງຊັນແປງຂໍ້ມູນຈາກ DataFrame ຂອງ 7mth2 ໃຫ້ເປັນຮູບແບບທີ່ FCS ຕ້ອງການ
# ------------------------------------------------------------
def parse_7mth2_row_to_match(row_dict, league_name="7mth2"):
    """
    ປັບຟັງຊັນນີ້ຕາມຊື່ຄໍລຳທີ່ພົບໃນຕາຕະລາງຈິງ.
    ທ່ານສາມາດດຶງຂໍ້ມູນເພີ່ມເຕີມ (ອັນດັບ, ຟອມ, ປະຕູ) ຈາກລິ້ງລາຍລະອຽດນັດຖ້າຕ້ອງການ.
    """
    # ສົມມຸດວ່າ DataFrame ມີຄໍລຳຢ່າງນ້ອຍ: ['เวลา', 'เจ้าบ้าน', 'แต้ม', 'ทีมเยือน', 'แต้มต่อ', 'ราคาบอล']
    # ທ່ານຄວນແລ່ນ script ກ່ອນເພື່ອເບິ່ງຊື່ຄໍລຳຕົວຈິງ (ພວກມັນຈະອອກເປັນພາສາໄທ ຫຼື ອັງກິດ)
    home_team = row_dict.get('เจ้าบ้าน', row_dict.get('Home', ''))
    away_team = row_dict.get('ทีมเยือน', row_dict.get('Away', ''))
    score = row_dict.get('แต้ม', row_dict.get('Score', '0-0'))
    handicap = row_dict.get('แต้มต่อ', row_dict.get('Hdp', '0'))
    
    # ກຳນົດທີມຕໍ່ຈາກ handicap (ເຄື່ອງໝາຍ '-' ໝາຍເຖິງເຈົ້າບ້ານຕໍ່)
    if isinstance(handicap, str):
        is_home_favorite = '-' in handicap
    else:
        is_home_favorite = False  # ຖ້າບໍ່ມີຂໍ້ມູນໃຫ້ຕັ້ງເປັນທີມບ້ານຮອງ
    
    # ອັນດັບ (ຕ້ອງການຂໍ້ມູນຈາກແຫຼ່ງອື່ນ, ຕົວຢ່າງນີ້ໃຊ້ຄ່າເລີ່ມຕົ້ນ)
    home_rank = extract_rank(row_dict.get('อันดับเจ้าบ้าน', row_dict.get('HomeRank', '10')))
    away_rank = extract_rank(row_dict.get('อันดับทีมเยือน', row_dict.get('AwayRank', '10')))
    
    # ຟອມ 5 ນັດ (ຕ້ອງດຶງຈາກລິ້ງລາຍລະອຽດ ຫຼື ກຳນົດເອງ)
    home_form = parse_form_string(row_dict.get('ฟอร์มเจ้าบ้าน', row_dict.get('HomeForm', 'DDDDD')))
    away_form = parse_form_string(row_dict.get('ฟอร์มทีมเยือน', row_dict.get('AwayForm', 'DDDDD')))
    
    # ປະຕູເສລີ່ຍ (ຕ້ອງການຂໍ້ມູນສະຖິຕິລີກ, ແທນທີ່ດ້ວຍຄ່າສະເລ່ຍລວມ)
    home_gf = extract_goals_avg(row_dict.get('ประตูเจ้าบ้าน', row_dict.get('HomeGF', '1.2')))
    home_ga = extract_goals_avg(row_dict.get('เสียเจ้าบ้าน', row_dict.get('HomeGA', '1.0')))
    away_gf = extract_goals_avg(row_dict.get('ประตูทีมเยือน', row_dict.get('AwayGF', '1.2')))
    away_ga = extract_goals_avg(row_dict.get('เสียทีมเยือน', row_dict.get('AwayGA', '1.0')))
    
    # Odds ເລີ່ມຕົ້ນຂອງທີມຕໍ່ (ຄໍລຳນີ້ອາດຊື່ 'ราคาบอล' ຫຼື 'O1')
    fav_odds = extract_odds(row_dict.get('ราคาบอล', row_dict.get('FavOdds', '1.85')))
    
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
        'h2h_matches': [],   # ສາມາດເພີ່ມພາຍຫຼັງໄດ້
        'is_home_favorite': is_home_favorite,
        'favorite_initial_odds': fav_odds,
        'error_count': 0
    }
    return match

def extract_rank(text):
    try:
        return int(re.search(r'\d+', str(text)).group())
    except:
        return 10

def parse_form_string(form_str):
    form_str = str(form_str).upper()
    return [ch for ch in form_str if ch in 'WDL']

def extract_goals_avg(val):
    try:
        return float(re.search(r'[\d\.]+', str(val)).group())
    except:
        return 1.0

def extract_odds(val):
    try:
        return float(re.search(r'[\d\.]+', str(val)).group())
    except:
        return 1.85

# ------------------------------------------------------------
# ຟັງຊັນຫຼັກ: ດຶງຂໍ້ມູນຈາກ 7mth2 ແລະ ວິເຄາະອັດຕະໂນມັດ
# ------------------------------------------------------------
def auto_analyze_7mth2():
    print("📥 ກຳລັງເປີດ 7mth2.com ແລະ ດຶງຂໍ້ມູນ...")
    df_raw, soup = scrape_7mth2_live(headless=True)
    print(f"✅ ດຶງຂໍ້ມູນສຳເລັດ: {len(df_raw)} ແຖວ")
    
    print("\n📋 ຕົວຢ່າງ 5 ແຖວທຳອິດ (ເພື່ອເບິ່ງໂຄງສ້າງ):")
    print(df_raw.head())
    print("\n📋 ລາຍຊື່ຄໍລຳທີ່ພົບ:")
    print(df_raw.columns.tolist())
    
    # ແປງແຕ່ລະແຖວ
    matches = []
    for idx, row in df_raw.iterrows():
        try:
            match = parse_7mth2_row_to_match(row.to_dict())
            matches.append(match)
        except Exception as e:
            print(f"⚠️ ຂ້າມແຖວ {idx} ຍ້ອນ: {e}")
    
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
# ເມື່ອຮຽກໃຊ້ໂດຍກົງ
# ------------------------------------------------------------
if __name__ == "__main__":
    result_df = auto_analyze_7mth2()
    
    print("\n📊 **ຜົນການວິເຄາະອັດຕະໂນມັດ (FCS V13.8)**")
    print(result_df.to_string(index=False))
    
    result_df.to_csv("7mth2_analysis.csv", index=False, encoding='utf-8-sig')
    print("\n💾 ບັນທຶກຜົນໄວ້ທີ່ 7mth2_analysis.csv")
