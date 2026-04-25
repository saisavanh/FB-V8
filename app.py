import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Goal7 Odds Data", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານ Goal7 (AH, OU, 1x2)")

def get_goal7_api_data():
    # ໃຊ້ API Link ໂດຍກົງທີ່ Goal7 ໃຊ້ດຶງຂໍ້ມູນມາສະແດງໃນເວັບ
    api_url = "https://goal7.co" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://goal7.co",
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        if response.status_code == 200:
            json_data = response.json()
            # ປົກກະຕິຂໍ້ມູນຈະຢູ່ໃນ json_data['data'] ຫຼື json_data['fixtures']
            # ຂ້ອຍຈະໃຊ້ວິທີກວດສອບໂຄງສ້າງ JSON ທີ່ພົບທົ່ວໄປໃນເວັບປະເພດນີ້
            items = json_data.get('data', json_data)
            
            if not items:
                return "ບໍ່ພົບຂໍ້ມູນການແຂ່ງຂັນໃນ API."

            match_list = []
            for item in items:
                # ດຶງຂໍ້ມູນພື້ນຖານ
                time = item.get('time', '--:--')
                league = item.get('league_name', 'ບໍ່ລະບຸລີກ')
                home = item.get('home_name', 'Unknown')
                away = item.get('away_name', 'Unknown')
                
                # ດຶງລາຄາ (Odds) - AH, OU, 1x2
                # ໝາຍເຫດ: ຊື່ Key ໃນ JSON ອາດຈະເປັນ hdp (Handicap), ou (OverUnder)
                ah = item.get('hdp', item.get('handicap', '0'))
                ou = item.get('ou', item.get('over_under', '0'))
                odd_1 = item.get('odd_1', '-') # ລາຄາເຈົ້າບ້ານຊະນະ
                odd_x = item.get('odd_x', '-') # ລາຄາສະເໝີ
                odd_2 = item.get('odd_2', '-') # ລາຄາທີມຢ້ຽມຊະນະ

                match_list.append({
                    "ເວລາ": time,
                    "ລີກ": league,
                    "ຄູ່ແຂ່ງ": f"{home} vs {away}",
                    "ລາຄາ AH": ah,
                    "ລາຄາ OU": ou,
                    "1x2 (H/D/A)": f"{odd_1} / {odd_x} / {odd_2}"
                })
            
            return pd.DataFrame(match_list)
        else:
            return f"Error {response.status_code}: ເຊີເວີ API ບໍ່ຕອບສະໜອງ"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນລາຄາທັງໝົດ'):
    with st.spinner('ກຳລັງເຊື່ອມຕໍ່ API ຂອງ Goal7...'):
        df = get_goal7_api_data()
        
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບທັງໝົດ {len(df)} ຄູ່")
            st.dataframe(df, use_container_width=True)
            
            # ສ້າງປຸ່ມ Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດໄຟລ໌ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'goal7_api_odds_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(df)

st.divider()
st.info("💡 ວິທີນີ້ຈະດຶງຂໍ້ມູນຈາກ API ໂດຍກົງ ເຊິ່ງຈະໄດ້ລາຄາທີ່ຊັດເຈນກວ່າການ Scraping ຈາກໜ້າ HTML.")

