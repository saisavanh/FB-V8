import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import urllib3

# ປິດຄຳເຕືອນ SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="ຕາຕະລາງບານເຕະ", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນວັນນີ້")

API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ລອງດຶງຂໍ້ມູນດ້ວຍ Timeout ທີ່ດົນຂຶ້ນ
        response = requests.get(url, headers=headers, timeout=25, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                return "ມື້ນີ້ຍັງບໍ່ມີການແຂ່ງຂັນໃນລະບົບ."
            
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
            return f"API ບໍ່ຕອບສະໜອງ (Code: {response.status_code})"
            
    except Exception as e:
        # ຖ້າເຊື່ອມຕໍ່ບໍ່ໄດ້ແທ້ໆ ໃຫ້ສະແດງຂໍ້ຄວາມແນະນຳ
        return "ບໍ່ສາມາດເຊື່ອມຕໍ່ກັບ API ໄດ້ໃນຂະນະນີ້. ກະລຸນາລອງໃໝ່ໃນອີກ 1-2 ນາທີ."

if st.button('🔄 ອັບເດດຕາຕະລາງ'):
    with st.spinner('ກຳລັງເຊື່ອມຕໍ່ກັບ API...'):
        result = get_matches()
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            st.dataframe(result, use_container_width=True)
        else:
            st.warning(result)
            st.info("💡 ຄຳແນະນຳ: ຖ້າຍັງບໍ່ໄດ້, ໃຫ້ໄປທີ່ 'Manage app' ແລ້ວເລືອກ 'Reboot app' ເພື່ອລ້າງ Error ຂອງ Server.")

st.divider()
st.caption("ຂໍ້ມູນຈາກ football-data.org | ເວລາລາວ GMT+7")

