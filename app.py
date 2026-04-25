import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="Goal7 Odds Crawler", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຕາຕະລາງບານ ແລະ ລາຄາ (AH, OU, 1x2)")

def scrape_goal7_detailed():
    url = "https://goal7.co"
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return f"Error {response.status_code}: ຖືກບລັອກການເຂົ້າເຖິງ"

        soup = BeautifulSoup(response.text, 'html.parser')
        # ຊອກຫາຕາຕະລາງການແຂ່ງຂັນ
        table = soup.find('table') 
        if not table:
            return "ບໍ່ພົບຕາຕະລາງຂໍ້ມູນໃນໜ້າເວັບ"

        rows = table.find_all('tr')
        all_matches = []
        current_league = "ທົ່ວໄປ"

        for row in rows:
            # ກວດສອບວ່າແມ່ນແຖວຂອງ "ລີກ" ຫຼື ບໍ່
            league_row = row.find('td', class_='league_name') or row.find('th')
            if league_row:
                current_league = league_row.get_text(strip=True)
                continue

            cols = row.find_all('td')
            if len(cols) >= 5:
                # ດຶງຂໍ້ມູນແຕ່ລະຊ່ອງ
                time = cols[0].get_text(strip=True)
                home_team = cols[2].get_text(strip=True)
                
                # --- ເຈາະດຶງລາຄາ AH ແລະ OU (ປົກກະຕິຢູ່ຖັນທີ 4) ---
                odds_col = cols[3]
                # Goal7 ມັກແຍກ AH ແລະ OU ດ້ວຍ <br> ຫຼື <span>
                odds_text = odds_col.get_text(" | ", strip=True) 
                
                away_team = cols[4].get_text(strip=True)
                
                # --- ເຈາະດຶງລາຄາ 1x2 (ປົກກະຕິຢູ່ຖັນທ້າຍໆ) ---
                odds_1x2 = ""
                if len(cols) >= 10:
                    odds_1x2 = cols[-1].get_text(strip=True)

                all_matches.append({
                    "ເວລາ": time,
                    "ລີກ": current_league,
                    "ທີມເຈົ້າບ້ານ": home_team,
                    "ລາຄາ AH / OU": odds_text,
                    "ທີມຢ້ຽມຢາມ": away_team,
                    "ລາຄາ 1x2": odds_1x2
                })

        return pd.DataFrame(all_matches)

    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ສ່ວນສະແດງຜົນ
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນພ້ອມລາຄາ'):
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນລາຄາ AH, OU, 1x2...'):
        df = scrape_goal7_detailed()
        
        if isinstance(df, pd.DataFrame):
            if not df.empty:
                st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບ {len(df)} ຄູ່")
                st.dataframe(df, use_container_width=True)
                
                # ປຸ່ມ Download
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 ດາວໂຫລດໄຟລ໌ CSV ເພື່ອວິເຄາະ", csv, "goal7_odds_full.csv", "text/csv")
            else:
                st.warning("ດຶງຂໍ້ມູນໄດ້ແຕ່ບໍ່ພົບລາຍການແຂ່ງຂັນ.")
        else:
            st.error(df)

st.divider()
st.caption("ຂໍ້ມູນຈາກ Goal7 | ໃຊ້ BeautifulSoup ເພື່ອເຈາະດຶງລາຄາໂດຍກົງ")

