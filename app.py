import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Football Data Analysis", page_icon="📊", layout="wide")

st.title("📊 ລະບົບດຶງຂໍ້ມູນບານເຕະເພື່ອການວິເຄາະ")
st.write("ດຶງຂໍ້ມູນ: ລາຄາ, ສະຖິຕິ, ແລະ ຜົນການແຂ່ງຂັນສົດ")

# ໃສ່ RapidAPI Key ຂອງທ່ານ (ສະໝັກຟຣີໄດ້ທີ່ ://rapidapi.com)
RAPID_API_KEY = "ໃສ່_API_KEY_ຂອງທ່ານ_ຢູ່ບ່ອນນີ້"

def get_all_data():
    url = "https://rapidapi.com"
    
    # ຕັ້ງຄ່າດຶງຂໍ້ມູນມື້ນີ້
    today = (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d')
    
    querystring = {"date": today}
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "://rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=20)
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('response', [])
            
            all_data = []
            for f in fixtures:
                all_data.append({
                    "Fixture_ID": f['fixture']['id'],
                    "Time": f['fixture']['date'],
                    "League": f['league']['name'],
                    "Country": f['league']['country'],
                    "Home_Team": f['teams']['home']['name'],
                    "Away_Team": f['teams']['away']['name'],
                    "Status": f['fixture']['status']['long'],
                    "Home_Score": f['goals']['home'],
                    "Away_Score": f['goals']['away'],
                    "Venue": f['fixture']['venue']['name']
                })
            return pd.DataFrame(all_data)
        else:
            return None
    except:
        return None

# ສ່ວນການສະແດງຜົນ ແລະ Download
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນທັງໝົດ'):
    with st.spinner('ກຳລັງປະມວນຜົນຂໍ້ມູນ...'):
        df = get_all_data()
        
        if df is not None and not df.empty:
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດທັງໝົດ {len(df)} ຄູ່!")
            
            # ສະແດງຕົວຢ່າງຂໍ້ມູນ
            st.dataframe(df)

            # ສ້າງປຸ່ມ Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig') # ໃຊ້ utf-8-sig ເພື່ອໃຫ້ Excel ອ່ານພາສາລາວ/ໄທໄດ້
            st.download_button(
                label="📥 ດາວໂຫລດຂໍ້ມູນເປັນ CSV (ສຳລັບ Excel)",
                data=csv,
                file_name=f'football_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error("ບໍ່ສາມາດດຶງຂໍ້ມູນໄດ້. ກະລຸນາກວດສອບ API Key ຫຼື ການເຊື່ອມຕໍ່.")

st.info("💡 ໝາຍເຫດ: ຂໍ້ມູນນີ້ລວມເອົາ Fixture ID ເຊິ່ງທ່ານສາມາດເອົາໄປດຶງ 'ສະຖິຕິລະອຽດ' (Stats) ຫຼື 'ລາຄາ' (Odds) ຕໍ່ໄດ້.")

