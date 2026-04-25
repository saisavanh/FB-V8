import streamlit as st
import pandas as pd
import cloudscraper
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Goal7 Data Exporter", page_icon="⚽", layout="wide")

st.title("⚽ ລະບົບດຶງຂໍ້ມູນບານເຕະ Goal7 (ສຳລັບວິເຄາະ)")
st.write("ດຶງຂໍ້ມູນຕາຕະລາງທັງໝົດ ແລະ ສົ່ງອອກເປັນໄຟລ໌ CSV")

def get_goal7_all():
    url = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
    
    try:
        # ໃຊ້ cloudscraper ເພື່ອຂ້າມ Cloudflare
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30)
        
        if response.status_code == 200:
            # ອ່ານຕາຕະລາງ HTML
            tables = pd.read_html(StringIO(response.text))
            
            if len(tables) > 0:
                # ເລືອກຕາຕະລາງທີ່ມີຂໍ້ມູນຫຼາຍທີ່ສຸດ (ຕາຕະລາງແຂ່ງຂັນ)
                df = max(tables, key=len)
                
                # ເຮັດຄວາມສະອາດຂໍ້ມູນເບື້ອງຕົ້ນ
                df = df.dropna(how='all', axis=1) # ລົບຖັນທີ່ວ່າງເປົ່າ
                return df
            else:
                return "ບໍ່ພົບຕາຕະລາງຂໍ້ມູນ."
        else:
            return f"Error {response.status_code}: ບໍ່ສາມາດເຂົ້າເຖິງ Goal7 ໄດ້."
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ປຸ່ມດຶງຂໍ້ມູນ
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນທຸກຄູ່'):
    with st.spinner('ກຳລັງເຈາະລະບົບປ້ອງກັນ ແລະ ດຶງຂໍ້ມູນ...'):
        data = get_goal7_all()
        
        if isinstance(data, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບທັງໝົດ {len(data)} ແຖວ")
            
            # ສະແດງຕາຕະລາງໃຫ້ເບິ່ງ
            st.dataframe(data, use_container_width=True)
            
            # ສ້າງປຸ່ມດາວໂຫລດ CSV
            csv = data.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດຂໍ້ມູນເປັນ CSV (ເປີດໃນ Excel)",
                data=csv,
                file_name=f'goal7_data_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                mime='text/csv',
            )
        else:
            st.error(data)

st.divider()
st.info("💡 ໝາຍເຫດ: ໄຟລ໌ CSV ທີ່ໄດ້ຈະລວມເອົາຂໍ້ມູນທຸກຢ່າງທີ່ປາກົດໃນຕາຕະລາງ Goal7 ເພື່ອໃຫ້ທ່ານນຳໄປກັ່ນຕອງວິເຄາະຕໍ່ໃນ Excel.")

