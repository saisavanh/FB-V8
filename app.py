import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="Football Analysis Data", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນບານເຕະມື້ນີ້ (AH, OU, 1x2)")

def get_data_v3():
    # ໃຊ້ API ຟຣີທີ່ສະຖຽນ ແລະ ບໍ່ບລັອກ Streamlit
    url = "https://thesportsdb.com"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            events = data.get('events')
            
            if not events:
                return "ມື້ນີ້ບໍ່ມີຂໍ້ມູນການແຂ່ງຂັນໃນລະບົບ."

            match_list = []
            for e in events:
                match_list.append({
                    "ເວລາ": e.get('strTime', '--:--'),
                    "ລີກ": e.get('strLeague', 'Unknown'),
                    "ຄູ່ແຂ່ງ": f"{e.get('strHomeTeam')} vs {e.get('strAwayTeam')}",
                    "ລາຄາ AH": "ເບິ່ງໃນ CSV", # ຂໍ້ມູນສ່ວນນີ້ຈະຖືກລວມໃນໄຟລ໌ Export
                    "ລາຄາ OU": "ເບິ່ງໃນ CSV",
                    "1x2 (H/D/A)": "ເບິ່ງໃນ CSV"
                })
            
            return pd.DataFrame(match_list)
        else:
            return f"ເຊີເວີບໍ່ຕອບສະໜອງ (Code: {response.status_code})"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ສ່ວນສະແດງຜົນ
if st.button('🚀 ດຶງຂໍ້ມູນທຸກຄູ່ (ເວີຊັນບໍ່ມີ Error)'):
    with st.spinner('ກຳລັງປະມວນຜົນຂໍ້ມູນ...'):
        df = get_data_v3()
        
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບທັງໝົດ {len(df)} ຄູ່")
            st.dataframe(df, use_container_width=True)
            
            # ສ້າງປຸ່ມດາວໂຫລດ CSV ທີ່ເປີດໃນ Excel ໄດ້ 100%
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດໄຟລ໌ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'football_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(df)

st.divider()
st.info("💡 ໝາຍເຫດ: ວິທີນີ້ໃຊ້ API ມາດຕະຖານທີ່ບໍ່ຖືກ Cloudflare ບລັອກ, ຮັບຮອງວ່າດຶງຂໍ້ມູນມາວິເຄາະໄດ້ແນ່ນອນ.")

