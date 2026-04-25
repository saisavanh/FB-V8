import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO

st.set_page_config(page_title="ຕາຕະລາງບານເຕະວັນນີ້", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະວັນນີ້")

def draw_data():
    url = "https://goal7.co"
    
    # ໃສ່ Header ເພື່ອໃຫ້ເວັບໄຊ້ຄິດວ່າແມ່ນ Browser ທົ່ວໄປເຂົ້າເບິ່ງ
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        # ໃຊ້ BeautifulSoup ຊອກຫາຕາຕະລາງ
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table') # ຊອກຫາທຸກຕາຕະລາງໃນເວັບ
        
        if tables:
            # ປ່ຽນ HTML table ເປັນ DataFrame ໂດຍໃຊ້ StringIO ເພື່ອປ້ອງກັນ Error ເລື່ອງ File Path
            all_df = pd.read_html(StringIO(str(tables[0])))
            df = all_df[0]
            return df
        else:
            return "ບໍ່ພົບຕາຕະລາງຂໍ້ມູນໃນເວັບໄຊ້"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {e}"

if st.button('ດຶງຂໍ້ມູນໃໝ່'):
    with st.spinner('ກຳລັງໂຫຼດຂໍ້ມູນ...'):
        result = draw_data()
        
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            # ສະແດງຕາຕະລາງ
            st.dataframe(result, use_container_width=True)
        else:
            st.error(result)
else:
    st.info("ກົດປຸ່ມດ້ານເທິງເພື່ອເລີ່ມດຶງຂໍ້ມູນ")

st.markdown("---")
st.caption("ໝາຍເຫດ: ຖ້າດຶງຂໍ້ມູນບໍ່ໄດ້ ອາດເປັນຍ້ອນເວັບໄຊ້ປ່ຽນໂຄງສ້າງ ຫຼື ບລັອກການເຂົ້າເຖິງ")
