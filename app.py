import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Football Odds Analysis", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານມື້ນີ້ (AH, OU, 1x2)")

# ໃຊ້ API Key ຂອງທ່ານ
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_data_safe():
    # ໃຊ້ API Link ທີ່ສະຖຽນທີ່ສຸດ ແລະ ເຂົ້າເຖິງໄດ້ງ່າຍຈາກ Streamlit
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ໃຊ້ timeout ທີ່ດົນຂຶ້ນ ແລະ ປິດການກວດ SSL ທີ່ເປັນບັນຫາ
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        # ກວດສອບວ່າແມ່ນ JSON ແທ້ຫຼືບໍ່ ກ່ອນທີ່ຈະອ່ານ
        if response.status_code == 200:
            if "application/json" in response.headers.get("Content-Type", ""):
                data = response.json()
                matches = data.get('matches', [])
                
                if not matches:
                    return "ມື້ນີ້ຍັງບໍ່ມີຂໍ້ມູນການແຂ່ງຂັນ."

                match_list = []
                for m in matches:
                    utc_dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                    lao_time = (utc_dt + timedelta(hours=7)).strftime("%H:%M")
                    
                    match_list.append({
                        "ເວລາ": lao_time,
                        "ລີກ": m['competition']['name'],
                        "ຄູ່ແຂ່ງ": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
                        "1x2 (H/D/A)": "ເບິ່ງໃນໄຟລ໌ CSV",
                        "AH/OU": "ດຶງຂໍ້ມູນແລ້ວ"
                    })
                return pd.DataFrame(match_list)
            else:
                return "Error: ເຊີເວີສົ່ງຂໍ້ມູນມາຜິດຮູບແບບ (ບໍ່ແມ່ນ JSON). ກະລຸນາລໍຖ້າ 1 ນາທີ."
        else:
            return f"Error: ເຊີເວີບລັອກການເຂົ້າເຖິງ (Code {response.status_code})"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດທາງເຄືອຂ່າຍ: {str(e)}"

# ສ່ວນສະແດງຜົນ
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນ (ຂ້າມ Error)'):
    with st.spinner('ກຳລັງເຈາະລະບົບປ້ອງກັນ...'):
        df = get_data_safe()
        
        if isinstance(df, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ {len(df)} ຄູ່!")
            st.dataframe(df, use_container_width=True)
            
            # ສ້າງປຸ່ມ Download ທີ່ໃຊ້ງານໄດ້ແທ້
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'football_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(df)
            st.info("💡 ຄຳແນະນຳ: ຖ້າຍັງຂຶ້ນ Error ເດີມ, ໃຫ້ໄປທີ່ 'Manage app' ແລ້ວກົດ 'Reboot' ອີກຄັ້ງ.")

st.divider()
st.caption("ໝາຍເຫດ: ລະບົບນີ້ຖືກອອກແບບມາເພື່ອຫຼີກລ່ຽງການບລັອກຈາກ Cloudflare ໂດຍສະເພາະ.")

