import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import urllib3

# ປິດການແຈ້ງເຕືອນເລື່ອງ Insecure Request (SSL verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="ຕາຕະລາງບານເຕະ", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນວັນນີ້")

# API Key ຂອງທ່ານ
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ສ້າງ Session ເພື່ອຈັດການການເຊື່ອມຕໍ່ໃຫ້ສະຖຽນຂຶ້ນ
        session = requests.Session()
        # ປິດ verify=False ເພື່ອຂ້າມ SSL Error ທີ່ທ່ານພົບ
        response = session.get(url, headers=headers, timeout=20, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                return "ມື້ນີ້ບໍ່ມີການແຂ່ງຂັນໃນລີກທີ່ຮອງຮັບ."
            
            match_list = []
            for m in matches:
                # ແປງເວລາ UTC ເປັນເວລາລາວ (+7)
                utc_dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                lao_time = (utc_dt + timedelta(hours=7)).strftime("%H:%M")
                
                match_list.append({
                    "ເວລາ": lao_time,
                    "ລີກ": m['competition']['name'],
                    "ທີມເຈົ້າບ້ານ": m['homeTeam']['name'],
                    "ທີມຢ້ຽມຢາມ": m['awayTeam']['name'],
                    "ສະຖານະ": m['status']
                })
            
            df = pd.DataFrame(match_list)
            return df.sort_values(by='ເວລາ')
        else:
            return f"Error: ເຊີເວີຕອບກັບດ້ວຍ Code {response.status_code}"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: ລະບົບເຊື່ອມຕໍ່ມີບັນຫາ, ກະລຸນາລອງໃໝ່ບຶດໜຶ່ງ"

if st.button('🔄 ອັບເດດຕາຕະລາງ'):
    with st.spinner('ກຳລັງໂຫຼດຂໍ້ມູນ...'):
        result = get_matches()
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            # ສະແດງເປັນຕາຕະລາງທີ່ເບິ່ງງ່າຍ
            st.table(result)
        else:
            st.error(result)

st.divider()
st.caption("ຂໍ້ມູນຈາກ football-data.org | ເວລາລາວ GMT+7")

