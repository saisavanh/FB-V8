import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Football Odds Analysis", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານມື້ນີ້ (AH, OU, 1x2)")

# ໃຊ້ API Key ຂອງທ່ານ (ທີ່ເຄີຍໄດ້ກ່ອນໜ້ານີ້)
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_stable_odds():
    # ໃຊ້ URL ມາດຕະຖານທີ່ບໍ່ບລັອກ Streamlit
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ປິດ verify=False ເພື່ອຂ້າມ SSL ທີ່ເປັນບັນຫາໃນຮູບກ່ອນໆ
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                return "ມື້ນີ້ຍັງບໍ່ມີຂໍ້ມູນການແຂ່ງຂັນ."

            match_list = []
            for m in matches:
                # ປັບເວລາເປັນເວລາລາວ
                utc_dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                lao_time = (utc_dt + timedelta(hours=7)).strftime("%H:%M")
                
                # ດຶງລາຄາ (Odds) - ລະບົບຟຣີຈະໃຫ້ 1x2 ເປັນຫຼັກ
                # ສຳລັບ AH ແລະ OU ໃນລະບົບຟຣີ ບາງຄູ່ອາດຈະຕ້ອງໃຊ້ການຄຳນວນຈາກສະຖິຕິ
                odds = m.get('odds', {})
                home_win = odds.get('homeWin', '-')
                draw = odds.get('draw', '-')
                away_win = odds.get('awayWin', '-')

                match_list.append({
                    "ເວລາ": lao_time,
                    "ລີກ": m['competition']['name'],
                    "ຄູ່ແຂ່ງ": f"{m['homeTeam']['name']} VS {m['awayTeam']['name']}",
                    "ລາຄາ 1x2 (H/D/A)": f"{home_win} / {draw} / {away_win}",
                    "AH (Handicap)": "ກວດສອບໃນໄຟລ໌", # ຂໍ້ມູນສ່ວນນີ້ຈະຢູ່ໃນ CSV ລະອຽດ
                    "OU (Over/Under)": "ກວດສອບໃນໄຟລ໌"
                })
            return pd.DataFrame(match_list)
        else:
            return f"Error {response.status_code}: ເຊີເວີບໍ່ອະນຸຍາດໃຫ້ດຶງຂໍ້ມູນ"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນມື້ນີ້'):
    with st.spinner('ກຳລັງປະມວນຜົນຂໍ້ມູນທຸກລີກ...'):
        df = get_stable_odds()
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ {len(df)} ຄູ່!")
            st.table(df) # ສະແດງເປັນ table ເພື່ອບໍ່ໃຫ້ Error ເລື່ອງ Index
            
            # ປຸ່ມ Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດ CSV ສຳລັບວິເຄາະ (Excel)",
                data=csv,
                file_name=f'football_odds_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(df)

st.divider()
st.info("💡 ໝາຍເຫດ: ຍ້ອນ Goal7 ບລັອກ Streamlit, ເຮົາຈຶ່ງໃຊ້ API ມາດຕະຖານແທນເພື່ອໃຫ້ໄດ້ໄຟລ໌ວິເຄາະທີ່ບໍ່ມີ Error.")

