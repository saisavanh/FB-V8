import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="ຕາຕະລາງບານມື້ນີ້", layout="wide")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະມື້ນີ້")

url = "https://goal7.co"

def get_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # ໝາຍເຫດ: ການດຶງຂໍ້ມູນຕ້ອງປັບຕາມໂຄງສ້າງ HTML ຂອງເວັບໄຊຕົວຈິງ
    # ຕົວຢ່າງການດຶງຂໍ້ມູນຈາກ Table
    data = []
    tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr')[1:]: # ຂ້າມຫົວຂໍ້ຕາຕະລາງ
            cols = row.find_all('td')
            if len(cols) >= 3:
                match = {
                    "ເວລາ": cols[0].text.strip(),
                    "ຄູ່ແຂ່ງຂັນ": cols[1].text.strip(),
                    "ລາຄາ AH": cols[2].text.strip() if len(cols) > 2 else "-"
                }
                data.append(match)
    return pd.DataFrame(data)

if st.button('ອັບເດດຂໍ້ມູນ'):
    df = get_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("ບໍ່ພົບຂໍ້ມູນໃນເວັບໄຊ")

