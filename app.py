import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import urllib3

# ປິດການແຈ້ງເຕືອນເລື່ອງ SSL ທີ່ບໍ່ປອດໄພ (ເພື່ອບໍ່ໃຫ້ມັນຂຶ້ນມາເຕືອນໃນໜ້າເວັບ)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານເຕະວັນນີ້", page_icon="⚽", layout="wide")

# ສ່ວນຫົວຂອງເວັບໄຊ້
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະວັນນີ້</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>ຂໍ້ມູນອັບເດດສົດໆ (ເວລາປະເທດລາວ 🇱🇦)</p>", unsafe_allow_html=True)

# API Key ຂອງທ່ານ
API_KEY = "6ed39fc3009f490997ee50b620f01b4c"

def get_matches():
    url = "https://football-data.org"
    headers = { 'X-Auth-Token': API_KEY }
    
    try:
        # ໃຊ້ verify=False ເພື່ອແກ້ Error SSL Certificate Verify Failed
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            if not matches:
                return "ມື້ນີ້ຍັງບໍ່ມີລາຍການແຂ່ງຂັນທີ່ຮອງຮັບໃນລະບົບຟຣີ."
            
            match_list = []
            for m in matches:
                # ດຶງເວລາ UTC ແລະ ບວກຕື່ມ 7 ຊົ່ວໂມງໃຫ້ເປັນເວລາລາວ
                utc_dt = datetime.strptime(m['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
                lao_dt = utc_dt + timedelta(hours=7)
                lao_time = lao_dt.strftime("%H:%M") 
                
                match_list.append({
                    "ເວລາແຂ່ງ": lao_time,
                    "ລາຍການ / ລີກ": m['competition']['name'],
                    "ທີມເຈົ້າບ້ານ": f"🏠 {m['homeTeam']['name']}",
                    "VS": "ພົບກັບ",
                    "ທີມຢ້ຽມຢາມ": f"🚀 {m['awayTeam']['name']}",
                    "ສະຖານະ": m['status']
                })
            
            # ແປງເປັນ DataFrame ແລະ ລຽງເວລາຈາກເຊົ້າໄປຫາເດິກ
            df = pd.DataFrame(match_list)
            return df.sort_values(by='ເວລາແຂ່ງ')
            
        elif response.status_code == 429:
            return "Error: ທ່ານກົດອັບເດດໄວເກີນໄປ (ກະລຸນາລໍຖ້າ 1 ນາທີ ແລ້ວລອງໃໝ່)."
        else:
            return f"ບໍ່ສາມາດເຊື່ອມຕໍ່ Server ໄດ້ (Code: {response.status_code})"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດທາງເຕັກນິກ: {str(e)}"

# ສ້າງປຸ່ມກົດອັບເດດ
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    update_btn = st.button('🔄 ອັບເດດຕາຕະລາງໃໝ່', use_container_width=True)

if update_btn:
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນ...'):
        result = get_matches()
        
        if isinstance(result, pd.DataFrame):
            st.success(f"ພົບການແຂ່ງຂັນທັງໝົດ {len(result)} ຄູ່ ສຳລັບມື້ນີ້")
            # ສະແດງຜົນເປັນຕາຕະລາງແບບ Static (ເບິ່ງງ່າຍໃນມືຖື)
            st.table(result)
        else:
            st.error(result)
else:
    st.info("💡 ກະລຸນາກົດປຸ່ມ 'ອັບເດດ' ດ້ານເທິງເພື່ອເບິ່ງຕາຕະລາງຂອງມື້ນີ້.")

# ສ່ວນທ້າຍເວັບ
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "<p>ພັດທະນາດ້ວຍ Streamlit Python | ຂໍ້ມູນຈາກ football-data.org</p>"
    "<p>ໝາຍເຫດ: ເວລາທີ່ສະແດງແມ່ນເວລາລາວ GMT+7</p>"
    "</div>", 
    unsafe_allow_html=True
)

