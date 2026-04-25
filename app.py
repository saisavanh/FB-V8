import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_data():
    url = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'  # ປ້ອງກັນພາສາໄທອ່ານບໍ່ອອກ
        soup = BeautifulSoup(response.content, 'html.parser')
        
        all_data = []
        # ເວັບໄຊນີ້ໃຊ້ Class 'table-bordered' ຫຼື ຕາຕະລາງຫຼາຍອັນແຍກຕາມລີກ
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                # ກວດສອບວ່າມີຂໍ້ມູນຄົບຕາມຮູບແບບ (ເວລາ, ເຈົ້າບ້ານ, ລາຄາ, ທີມຢືນ)
                if len(cols) >= 6:
                    time = cols[0].text.strip()
                    home_team = cols[3].text.strip()
                    price = cols[4].text.strip()
                    away_team = cols[5].text.strip()
                    
                    # ກວດສອບບໍ່ໃຫ້ດຶງເອົາແຖວທີ່ເປັນຫົວຂໍ້ "ເວລາ", "ທົງ", "ສົດ"
                    if time != "ເວລາ" and ":" in time:
                        all_data.append({
                            "ເວລາ": time,
                            "ຄູ່ແຂ່ງຂັນ": f"{home_team} vs {away_team}",
                            "ລາຄາ AH": price
                        })
        
        return pd.DataFrame(all_data)
    except Exception as e:
        st.error(f"ເກີດຂໍ້ຜິດພາດ: {e}")
        return pd.DataFrame()

# ສ່ວນສະແດງຜົນ Streamlit
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະມື້ນີ້")
if st.button('ອັບເດດຂໍ້ມູນ'):
    df = get_data()
    if not df.empty:
        st.table(df) # ໃຊ້ st.table ເພື່ອໃຫ້ເບິ່ງງ່າຍຄືໃນຮູບ
    else:
        st.warning("ບໍ່ພົບຂໍ້ມູນການແຂ່ງຂັນໃນເວລານີ້")

