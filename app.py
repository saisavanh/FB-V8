import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານເຕະວັນນີ້", page_icon="⚽")

st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະວັນນີ້")
st.write("ຂໍ້ມູນດຶງມາຈາກ: Goal7")

# ຟັງຊັນດຶງຂໍ້ມູນ
def draw_data():
    url = "https://goal7.co"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ຊອກຫາຕາຕະລາງ (ປັບຕາມໂຄງສ້າງເວັບໄຊ້)
        tables = pd.read_html(response.text)
        if tables:
            df = tables[0] # ເອົາຕາຕະລາງທຳອິດ
            # ປ່ຽນຊື່ຫົວຂໍ້ເປັນພາສາລາວ
            df.columns = ['ເວລາ', 'ລີກ', 'ທີມເຈົ້າບ້ານ', 'ລາຄາ', 'ທີມຢ້ຽມຢາມ', 'ຖ່າຍທອດສົດ']
            return df
        else:
            return None
    except Exception as e:
        st.error(f"ບໍ່ສາມາດດຶງຂໍ້ມູນໄດ້: {e}")
        return None

# ສະແດງປຸ່ມກົດດຶງຂໍ້ມູນ
if st.button('ອັບເດດຂໍ້ມູນໃໝ່'):
    data = draw_data()
    if data is not None:
        st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
        st.dataframe(data, use_container_width=True)
    else:
        st.warning("ບໍ່ພົບຂໍ້ມູນໃນເວັບໄຊ້.")
else:
    st.info("ກະລຸນາກົດປຸ່ມດ້ານເທິງເພື່ອເບິ່ງຕາຕະລາງ")

st.markdown("---")
st.caption("ພັດທະນາດ້ວຍ Streamlit | ພາສາລາວ 100%")

