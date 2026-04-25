import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import certifi

st.set_page_config(page_title="ຕາຕະລາງບານເຕະ", page_icon="⚽")
st.title("⚽ ຕາຕະລາງບານເຕະວັນນີ້")

API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    # ປ່ຽນກັບມາໃຊ້ https ແລະ ໃຊ້ certifi ເພື່ອຢືນຢັນ SSL ໃຫ້ຖືກຕ້ອງ
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ໃຊ້ verify=certifi.where() ເພື່ອແກ້ Error SSL ແບບປອດໄພ
        response = requests.get(url, headers=headers, timeout=20, verify=certifi.where())
        
        if response.status_code == 200:
            data = response.json()
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
        else:
            return f"ເຊີເວີຕອບກັບດ້ວຍ Code: {response.status_code} (ອາດຈະຖືກບລັອກຊົ່ວຄາວ)"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🔄 ອັບເດດຂໍ້ມູນ'):
    with st.spinner('ກຳລັງໂຫຼດ...'):
        result = get_matches()
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            st.table(result) # ໃຊ້ table ຈະສະແດງຜົນໄດ້ຄົບຖ້ວນກວ່າໃນມືຖື
        else:
            st.error(result)

st.caption("ຂໍ້ມູນຈາກ football-data.org | ເວລາລາວ GMT+7")

