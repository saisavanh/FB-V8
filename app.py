import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Football Data Analysis", page_icon="⚽", layout="wide")
st.title("⚽ ດຶງຂໍ້ມູນລາຄາບານ Goal7 (AH, OU, 1x2)")

def get_goal7_final():
    url = "https://goal7.co"
    
    try:
        # ສ້າງ Scraper ທີ່ຈຳລອງເປັນ Chrome Browser ແທ້ໆ
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        response = scraper.get(url, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # ໃຊ້ BeautifulSoup ເພື່ອຊອກຫາຕາຕະລາງ
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            
            if table:
                df = pd.read_html(StringIO(str(table)))[0]
                
                # ເຮັດຄວາມສະອາດຂໍ້ມູນ: ເອົາແຕ່ຖັນທີ່ມີຂໍ້ມູນລາຄາ
                # Goal7: ຖັນ 0=ເວລາ, 1=ລີກ, 2=ເຈົ້າບ້ານ, 3=ລາຄາ(AH/OU), 4=ຢ້ຽມຢາມ, 11=1x2
                final_df = pd.DataFrame()
                final_df['ເວລາ'] = df.iloc[:, 0]
                final_df['ລີກ'] = df.iloc[:, 1]
                final_df['ຄູ່ແຂ່ງ'] = df.iloc[:, 2].astype(str) + " vs " + df.iloc[:, 4].astype(str)
                final_df['ລາຄາ AH / OU'] = df.iloc[:, 3]
                
                # ຖ້າຖັນ 1x2 ມີ (ປົກກະຕິຢູ່ຖັນທີ 11)
                if len(df.columns) >= 12:
                    final_df['1x2 / ອື່ນໆ'] = df.iloc[:, 11]
                
                return final_df
            else:
                return "Error: ບໍ່ພົບຕາຕະລາງໃນໜ້າເວັບ (ເວັບໄຊ້ອາດຈະມີການປ່ຽນແປງ)"
        else:
            return f"Error {response.status_code}: ຖືກ Cloudflare ບລັອກຊົ່ວຄາວ"
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ສ່ວນສະແດງຜົນ
if st.button('🚀 ເລີ່ມດຶງຂໍ້ມູນ (ເວີຊັນເຈາະ Cloudflare)'):
    with st.spinner('ກຳລັງຂ້າມລະບົບປ້ອງກັນຂອງ Goal7...'):
        result = get_goal7_final()
        
        if isinstance(result, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບ {len(result)} ຄູ່")
            st.dataframe(result, use_container_width=True)
            
            # ປຸ່ມດາວໂຫລດ CSV
            csv = result.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'goal7_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(result)
            st.info("💡 ຖ້າຍັງບໍ່ໄດ້: ໃຫ້ລໍຖ້າ 5 ນາທີ ແລ້ວກົດ Reboot App ໃໝ່ ເພາະ IP ຂອງ Server ອາດຈະຖືກບລັອກຊົ່ວຄາວ.")

st.divider()
st.caption("ຂໍ້ມູນຈາກ Goal7 | ໃຊ້ CloudScraper ເພື່ອຂ້າມລະບົບປ້ອງກັນ")

