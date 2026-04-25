import streamlit as st
import pandas as pd
import requests

# ຕັ້ງຄ່າໜ້າເວັບ
st.set_page_config(page_title="ຕາຕະລາງບານເຕະ", page_icon="⚽")
st.title("⚽ ຕາຕະລາງການແຂ່ງຂັນບານເຕະວັນນີ້")

def draw_data():
    # ໃຊ້ API Link ໂດຍກົງຈາກ Goal7 (ອັນນີ້ຈະໄດ້ຂໍ້ມູນແນ່ນອນ)
    api_url = "https://goal7.co" 
    
    # ຖ້າ API ເທິງບໍ່ເຮັດວຽກ ເຮົາຈະໃຊ້ວິທີດຶງຈາກ JSON ທີ່ຊ່ອນຢູ່ໃນເວັບ
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://goal7.co"
    }

    try:
        # ລອງດຶງຂໍ້ມູນແບບ JSON
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # ແປງຂໍ້ມູນ JSON ເປັນ DataFrame (ຈັດລຽງຖັນໃຫ້ງາມ)
            df = pd.DataFrame(data['data']) # ປັບຕາມໂຄງສ້າງ JSON ຂອງເຂົາເຈົ້າ
            return df
        else:
            # ຖ້າ API ໂດຍກົງບໍ່ໄດ້, ໃຫ້ໃຊ້ວິທີອ່ານ HTML ແບບລະອຽດ
            url = "https://goal7.co%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
            all_tables = pd.read_html(url, encoding='utf-8')
            if len(all_tables) > 0:
                return all_tables[0] # ເອົາຕາຕະລາງທຳອິດທີ່ພົບ
            return "ບໍ່ພົບຂໍ້ມູນຕາຕະລາງ"

    except Exception as e:
        return f"ເກີດຂໍ້ຜິດພາດ: ລະບົບປ້ອງກັນການດຶງຂໍ້ມູນ ຫຼື ໂຄງສ້າງເວັບປ່ຽນແປງ"

if st.button('🔄 ອັບເດດຂໍ້ມູນ'):
    with st.spinner('ກຳລັງໂຫຼດ...'):
        result = draw_data()
        
        if isinstance(result, pd.DataFrame):
            st.success("ດຶງຂໍ້ມູນສຳເລັດ!")
            # ປັບແຕ່ງການສະແດງຜົນໃຫ້ເບິ່ງງ່າຍ
            st.dataframe(result, use_container_width=True)
        else:
            st.error(result)
            st.info("💡 ແນະນຳ: ລອງກົດປຸ່ມ 'ອັບເດດ' ອີກຄັ້ງ ຫຼື ກວດສອບອິນເຕີເນັດ")

st.markdown("---")
st.caption("ຂໍ້ມູນຈາກ Goal7 | ອັບເດດອັດຕະໂນມັດ")

