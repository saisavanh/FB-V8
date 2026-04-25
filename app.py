import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານ Goal7", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນຈາກ Goal7")

def draw_goal7_data():
    url = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
    
    # ໃສ່ Header ເພື່ອປອມຕົວເປັນ Browser ປ້ອງກັນການຖືກບລັອກ
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        # ດຶງຂໍ້ມູນ HTML ຈາກເວັບໄຊ້
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8' # ໃຫ້ຮອງຮັບພາສາໄທ/ລາວ
        
        if response.status_code == 200:
            # ໃຊ້ Pandas ອ່ານຕາຕະລາງຈາກ HTML ໂດຍກົງ
            # ໃສ່ StringIO ເພື່ອປ້ອງກັນ Error ເລື່ອງການອ່ານ string
            tables = pd.read_html(StringIO(response.text))
            
            if len(tables) > 0:
                # ປົກກະຕິຕາຕະລາງບານຈະຢູ່ Index 0 ຫຼື 1
                df = tables[0] 
                
                # ປ່ຽນຊື່ຫົວຂໍ້ເປັນພາສາລາວ (ຖ້າຈຳນວນຖັນກົງກັນ)
                if len(df.columns) >= 5:
                    df.columns = ['ເວລາ', 'ລີກ', 'ທີມເຈົ້າບ້ານ', 'ລາຄາ', 'ທີມຢ້ຽມຢາມ', 'ຊ່ອງຖ່າຍທອດ'][:len(df.columns)]
                
                return df
            else:
                return "ບໍ່ພົບຕາຕະລາງຂໍ້ມູນໃນໜ້າເວັບ Goal7"
        else:
            return f"ບໍ່ສາມາດເຂົ້າເຖິງເວັບໄຊ້ໄດ້ (Code: {response.status_code})"
            
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ປຸ່ມກົດອັບເດດ
if st.button('🔄 ດຶງຂໍ້ມູນຈາກ Goal7'):
    with st.spinner('ກຳລັງໂຫຼດຂໍ້ມູນ...'):
        result = draw_goal7_data()
        
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            st.dataframe(result, use_container_width=True)
        else:
            st.error(result)
            st.info("💡 ຄຳແນະນຳ: ຖ້າຂຶ້ນ Error 403 ໝາຍຄວາມວ່າເວັບໄຊ້ບລັອກ Server ຂອງ Streamlit.")

st.divider()
st.caption("ແຫຼ່ງຂໍ້ມູນ: Goal7.co | ພັດທະນາດ້ວຍ Streamlit")

