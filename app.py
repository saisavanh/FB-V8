import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານເຕະ", page_icon="⚽")

st.markdown("<h1 style='text-align: center;'>⚽ ຕາຕະລາງບານເຕະວັນນີ້</h1>", unsafe_allow_html=True)

# API Key ຂອງທ່ານ
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    # ປ່ຽນ URL ເປັນ http ເພື່ອຫຼີກລ່ຽງບັນຫາ SSL Certificate verify failed
    url = "http://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ໃຊ້ verify=False ແລະ ຈັດການ Header ໃຫ້ເໝືອນ Browser ທົ່ວໄປ
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code == 200:
            try:
                data = response.json()
            except:
                return "Error: ເຊີເວີສົ່ງຂໍ້ມູນມາຜິດຮູບແບບ (ບໍ່ແມ່ນ JSON)"

            matches = data.get('matches', [])
            if not matches:
                return "ມື້ນີ້ບໍ່ມີການແຂ່ງຂັນໃນລີກທີ່ຮອງຮັບ."
            
            match_list = []
            for m in matches:
                utc_dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                lao_time = (utc_dt + timedelta(hours=7)).strftime("%H:%M")
                
                match_list.append({
                    "ເວລາ": lao_time,
                    "ລີກ": m['competition']['name'],
                    "ຄູ່ແຂ່ງ": f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}",
                    "ສະຖານະ": m['status']
                })
            return pd.DataFrame(match_list)
        elif response.status_code == 429:
            return "ກະລຸນາລໍຖ້າ 1 ນາທີ (API ໃຫ້ດຶງຂໍ້ມູນຈຳກັດ)"
        else:
            return f"ເຊີເວີຕອບກັບດ້ວຍ Code: {response.status_code}"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🔄 ອັບເດດຂໍ້ມູນ'):
    with st.spinner('ກຳລັງໂຫຼດ...'):
        result = get_matches()
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            st.dataframe(result, use_container_width=True)
        else:
            st.error(result)

st.caption("ຂໍ້ມູນຈາກ football-data.org | ເວລາລາວ GMT+7")

