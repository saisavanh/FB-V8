import streamlit as st
import pandas as pd
import cloudscraper
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="Goal7 Odds Exporter", page_icon="⚽", layout="wide")

st.title("⚽ ລະບົບດຶງຕາຕະລາງ ແລະ ອັດຕາຕໍ່ລອງ Goal7")
st.write("ຂໍ້ມູນທີ່ດຶງ: 1x2, Asian Handicap (AH), ແລະ Over/Under (OU)")

def get_goal7_odds():
    url = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
    
    try:
        # ໃຊ້ cloudscraper ເພື່ອຂ້າມ Cloudflare
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # ອ່ານຕາຕະລາງ HTML
            tables = pd.read_html(StringIO(response.text))
            
            if len(tables) > 0:
                # ເລືອກຕາຕະລາງການແຂ່ງຂັນ (ຕາຕະລາງທີ່ມີແຖວຫຼາຍສຸດ)
                df = max(tables, key=len)
                
                # --- ສ່ວນການເລືອກຖັນ (Goal7 ປົກກະຕິມີ 12 ຖັນ) ---
                # ເຮົາຈະເລືອກເອົາຖັນທີ່ກ່ຽວຂ້ອງກັບລາຄາ AH, 1x2, OU
                # ໝາຍເຫດ: Index ຂອງຖັນອາດປ່ຽນແປງຕາມເວັບໄຊ້, ເຮົາຈະເລືອກຖັນຫຼັກໆດັ່ງນີ້:
                
                # ຕົວຢ່າງການເລືອກຖັນ (ປັບຕາມໂຄງສ້າງ Goal7 ຕົວຈິງ)
                # ຖັນ 0: ເວລາ, 1: ລີກ, 2: ເຈົ້າບ້ານ, 3: ລາຄາ AH/OU, 4: ທີມຢ້ຽມ, 11: 1x2
                
                # ເພື່ອໃຫ້ແນ່ນອນ ເຮົາຈະດຶງມາທັງໝົດກ່ອນ ແລ້ວໃຫ້ຜູ້ໃຊ້ເລືອກ ຫຼື ຕັດໃຫ້ເຫຼືອແຕ່ທີ່ຕ້ອງການ
                # ໃນທີ່ນີ້ຂ້ອຍຈະຕັ້ງຊື່ໃຫ້ໃໝ່ຕາມທີ່ທ່ານຕ້ອງການ:
                new_df = df.copy()
                
                # ສ້າງ DataFrame ໃໝ່ທີ່ມີແຕ່ຂໍ້ມູນທີ່ທ່ານຕ້ອງການ
                final_df = pd.DataFrame()
                final_df['ເວລາ'] = new_df.iloc[:, 0]
                final_df['ລີກ'] = new_df.iloc[:, 1]
                final_df['ຄູ່ແຂ່ງ'] = new_df.iloc[:, 2] + " vs " + new_df.iloc[:, 4]
                final_df['ອັດຕາຕໍ່ລອງ (AH/OU)'] = new_df.iloc[:, 3] # ສ່ວນຫຼາຍ Goal7 ລວມ AH/OU ໄວ້ຖັນດຽວກັນ
                final_df['ລາຄາ 1x2'] = new_df.iloc[:, -1] # ຖັນສຸດທ້າຍມັກຈະແມ່ນ 1x2 ຫຼື ຊ່ອງຖ່າຍທອດ
                
                return final_df
            else:
                return "ບໍ່ພົບຂໍ້ມູນຕາຕະລາງ."
        else:
            return f"Error {response.status_code}: ເວັບໄຊ້ບລັອກການເຂົ້າເຖິງ."
    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: {str(e)}"

# ປຸ່ມດຶງຂໍ້ມູນ
if st.button('🚀 ດຶງຂໍ້ມູນອັດຕາຕໍ່ລອງທຸກຄູ່'):
    with st.spinner('ກຳລັງດຶງຂໍ້ມູນຈາກ Goal7...'):
        data = get_goal7_odds()
        
        if isinstance(data, pd.DataFrame):
            st.success(f"ດຶງຂໍ້ມູນສຳເລັດ! ພົບທັງໝົດ {len(data)} ຄູ່")
            
            # ສະແດງຕາຕະລາງ
            st.dataframe(data, use_container_width=True)
            
            # ປຸ່ມ Download CSV
            csv = data.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ດາວໂຫລດໄຟລ໌ CSV ສຳລັບວິເຄາະ",
                data=csv,
                file_name=f'goal7_odds_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
            )
        else:
            st.error(data)

st.divider()
st.info("💡 ຄຳແນະນຳ: ຖ້າຂໍ້ມູນໃນຖັນບໍ່ກົງ, ທ່ານສາມາດບອກໃຫ້ຂ້ອຍປັບ Index ຂອງຖັນໃໝ່ໄດ້ ຫຼັງຈາກທີ່ທ່ານເຫັນຜົນລັດທຳອິດ.")

