import streamlit as st
import pandas as pd
import requests
from io import StringIO

st.set_page_config(page_title="Goal7 Table", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນຈາກ Goal7")

def draw_goal7_data():
    url = "https://goal7.co"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # ດຶງຕາຕະລາງທັງໝົດອອກມາ
            tables = pd.read_html(StringIO(response.text))
            
            if len(tables) > 0:
                # ເລືອກຕາຕະລາງທີ່ຄິດວ່າແມ່ນຕາຕະລາງບານ (ປົກກະຕິແມ່ນຕາຕະລາງທີ່ມີຂໍ້ມູນຫຼາຍທີ່ສຸດ)
                df = max(tables, key=len)
                return df
            else:
                return "ບໍ່ພົບຕາຕະລາງຂໍ້ມູນ."
        else:
            return f"Error {response.status_code}: ເວັບໄຊ້ບລັອກການເຂົ້າເຖິງ."
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

if st.button('🔄 ດຶງຂໍ້ມູນໃໝ່'):
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນ...'):
        result = draw_goal7_data()
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            # ສະແດງຕາຕະລາງທັງໝົດທີ່ດຶງມາໄດ້ໂດຍບໍ່ຕ້ອງກຳນົດຊື່ຖັນ
            st.dataframe(result, use_container_width=True)
        else:
            st.error(result)

st.divider()
st.caption("ແຫຼ່ງຂໍ້ມູນ: Goal7.co | ພັດທະນາດ້ວຍ Streamlit")

