import streamlit as st
import pandas as pd
import cloudscraper
import json
from datetime import datetime

st.set_page_config(page_title="Goal7 Data Analysis", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານ Goal7 (AH, OU, 1x2)")

def get_goal7_api_direct():
    # URL ຂອງ API ທີ່ Goal7 ໃຊ້ດຶງຂໍ້ມູນມາສະແດງ (ອັນນີ້ຄືຫົວໃຈສຳຄັນ)
    api_url = "https://goal7.co" 
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(api_url, timeout=30)
        
        if response.status_code == 200:
            # ຖ້າໄດ້ຂໍ້ມູນເປັນ JSON
            data = response.json()
            fixtures = data.get('data', []) # ປັບຕາມໂຄງສ້າງ JSON ຂອງ Goal7
            
            if not fixtures:
                return "ບໍ່ພົບຂໍ້ມູນການແຂ່ງຂັນໃນ API ຂອງ Goal7."

            final_list = []
            for f in fixtures:
                final_list.append({
                    "ເວລາ": f.get('time'),
                    "ລີກ": f.get('league_name'),
                    "ຄູ່ແຂ່ງ": f"{f.get('home_name')} vs {f.get('away_name')}",
                    "ລາຄາ AH": f.get('hdp'),
                    "ລາຄາ OU": f.get('ou'),
                    "ລາຄາ 1x2": f"{f.get('odd_1')} / {f.get('odd_x')} / {f.get('odd_2')}"
                })
            return pd.DataFrame(final_list)
        else:
            return f"Error {response.status_code}: ບໍ່ສາມາດເຊື່ອມຕໍ່ API ໄດ້."
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ສ່ວນສະແດງຜົນ
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນ (Direct API)'):
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນຈາກ API ຂອງ Goal7...'):
        df = get_goal7_api_direct()
        
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບທັງໝົດ {len(df)} ຄູ່")
            st.dataframe(df, use_container_width=True)
            
            # ປຸ່ມ Download CSV
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'goal7_odds_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(df)

st.divider()
st.info("💡 ວິທີນີ້ເປັນການດຶງຂໍ້ມູນ JSON ໂດຍກົງ, ເຮັດໃຫ້ໄດ້ລາຄາ AH, OU, 1x2 ທີ່ຊັດເຈນທີ່ສຸດ.")

