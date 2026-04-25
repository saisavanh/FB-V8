import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Football Odds Analysis", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານມື້ນີ້ (AH, OU, 1x2)")

# --- ທ່ານຕ້ອງໃສ່ RapidAPI Key ຂອງທ່ານບ່ອນນີ້ ---
# ສະໝັກຟຣີໄດ້ທີ່: https://rapidapi.com
API_KEY = "6ed39fc3009f490997ee50b620f01b4c" # ຖ້າມີ Key ໃໝ່ໃຫ້ປ່ຽນໃສ່ນີ້

def get_data_success():
    # ໃຊ້ API-Football ເຊິ່ງໃຫ້ລາຄາ AH, OU, 1x2 ຄົບຖ້ວນ
    url = "https://rapidapi.com"
    today = (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d')
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "://rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params={"date": today}, timeout=20)
        if response.status_code == 200:
            data = response.json().get('response', [])
            if not data: return "ມື້ນີ້ຍັງບໍ່ມີຂໍ້ມູນລາຄາໃນລະບົບ."

            match_list = []
            for item in data:
                # ດຶງລາຄາຈາກ Bookmaker ຕົວທຳອິດ
                bookmaker = item['bookmakers'][0]
                bets = bookmaker['bets']
                
                res = {
                    "ເວລາ": item['fixture']['date'][11:16],
                    "ລີກ": item['league']['name'],
                    "ຄູ່ແຂ່ງ": f"{item['teams']['home']['name']} vs {item['teams']['away']['name']}",
                    "1x2 (H/D/A)": "-",
                    "AH (Handicap)": "-",
                    "OU (Over/Under)": "-"
                }

                for bet in bets:
                    if bet['name'] == "Match Winner":
                        res["1x2 (H/D/A)"] = f"{bet['values'][0]['odd']} / {bet['values'][1]['odd']} / {bet['values'][2]['odd']}"
                    if bet['name'] == "Asian Handicap":
                        res["AH (Handicap)"] = f"{bet['values'][0]['value']} ({bet['values'][0]['odd']})"
                    if bet['name'] == "Goals Over/Under":
                        res["OU (Over/Under)"] = f"{bet['values'][0]['value']} ({bet['values'][0]['odd']})"
                
                match_list.append(res)
            return pd.DataFrame(match_list)
        else:
            return f"API Error: {response.status_code}. ກະລຸນາກວດສອບ Key ຂອງທ່ານ."
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🚀 ດຶງຂໍ້ມູນມື້ນີ້ (AH, OU, 1x2)'):
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນລາຄາຈາກ API...'):
        df = get_data_success()
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບ {len(df)} ຄູ່")
            st.dataframe(df, use_container_width=True)
            
            # ປຸ່ມ Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ດາວໂຫລດ CSV ສຳລັບວິເຄາະ", csv, "football_odds.csv", "text/csv")
        else:
            st.error(df)

st.divider()
st.info("💡 ໝາຍເຫດ: ຍ້ອນ Goal7 ບລັອກ Streamlit, ວິທີນີ້ເປັນວິທີດຽວທີ່ຈະໄດ້ລາຄາ AH, OU, 1x2 ທີ່ສະຖຽນທີ່ສຸດ.")

