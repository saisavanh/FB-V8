import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານເຕະວັນນີ້", page_icon="⚽", layout="wide")

# ສ່ວນຫົວຂອງເວັບໄຊ້
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະວັນນີ້</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>ຂໍ້ມູນອັບເດດສົດໆຈາກ Global Football API</p>", unsafe_allow_html=True)

# ໃສ່ API Key ຂອງທ່ານ
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                return "ມື້ນີ້ຍັງບໍ່ມີລາຍການແຂ່ງຂັນທີ່ຮອງຮັບ."
            
            match_list = []
            for m in matches:
                # ແປງເວລາ UTC ເປັນເວລາທີ່ອ່ານງ່າຍ
                dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                thai_time = dt.strftime("%H:%M") # ເວລາແຂ່ງ
                
                match_list.append({
                    "ເວລາ": thai_time,
                    "ລີກ / ລາຍການ": m['competition']['name'],
                    "ທີມເຈົ້າບ້ານ": f"🏠 {m['homeTeam']['name']}",
                    "VS": "ພົບກັບ",
                    "ທີມຢ້ຽມຢາມ": f"🚀 {m['awayTeam']['name']}",
                    "ສະຖານະ": m['status']
                })
            return pd.DataFrame(match_list)
        elif response.status_code == 429:
            return "Error: ທ່ານກົດອັບເດດໄວເກີນໄປ (ກະລຸນາລໍຖ້າ 1 ນາທີ)."
        else:
            return f"ບໍ່ສາມາດດຶງຂໍ້ມູນໄດ້ (Error {response.status_code})"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {e}"

# ສ້າງປຸ່ມອັບເດດ
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    update_btn = st.button('🔄 ກົດເພື່ອເບິ່ງຕາຕະລາງໃໝ່', use_container_width=True)

if update_btn:
    with st.spinner('ກຳລັງໂຫຼດຂໍ້ມູນ...'):
        result = get_matches()
        if isinstance(result, pd.DataFrame):
            st.success(f"ພົບການແຂ່ງຂັນທັງໝົດ {len(result)} ຄູ່")
            # ສະແດງຕາຕະລາງແບບບໍ່ມີ Index ເພື່ອໃຫ້ງາມ
            st.table(result)
        else:
            st.error(result)
else:
    st.info("ກະລຸນາກົດປຸ່ມ 'ອັບເດດ' ດ້ານເທິງເພື່ອດຶງຂໍ້ມູນການແຂ່ງຂັນຂອງມື້ນີ້.")

# ສ່ວນທ້າຍ
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>ພັດທະນາດ້ວຍ Streamlit | ຂໍ້ມູນຈາກ Football-Data.org</p>", unsafe_allow_html=True)

