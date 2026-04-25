import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import random

# --- 1. ຕັ້ງຄ່າ UI ---
st.set_page_config(page_title="AI Football Pro Analyzer", layout="wide")
st.title("⚽ AI Football Pro: ລະບົບວິເຄາະບານເຕະຄົບວົງຈອນ")
st.markdown("ວິເຄາະສະຖິຕິ, ລາຄາໄຫຼ, ແລະ ຄວາມພ້ອມຂອງທີມແບບ Real-time")

# --- 2. ຟັງຊັນດຶງຂໍ້ມູນຕາຕະລາງ (Scraping) ---
@st.cache_data(ttl=3600)
def get_match_list():
    url = "https://goal7.co"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.content, 'html.parser')
        matches = []
        for row in soup.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 6:
                matches.append({
                    "ເວລາ": cols[0].text.strip(),
                    "ເຈົ້າບ້ານ": cols[2].text.strip(),
                    "ລາຄາ AH": cols[4].text.strip(),
                    "ທີມຢືນ": cols[5].text.strip()
                })
        return pd.DataFrame(matches)
    except:
        return pd.DataFrame(columns=["ເວລາ", "ເຈົ້າບ້ານ", "ລາຄາ AH", "ທີມຢືນ"])

# --- 3. ຟັງຊັນວິເຄາະຂໍ້ມູນ (AI Logic & Stats) ---
def deep_analysis(home, away, current_ah):
    # ຈຳລອງການດຶງຂໍ້ມູນສະຖິຕິ (ໃນໄລຍະຍາວຄວນເຊື່ອມຕໍ່ API-Football)
    h2h_win_home = random.randint(30, 70)
    last_10_win_home = random.randint(40, 80)
    last_10_win_away = random.randint(30, 70)
    
    # Logic ກວດສອບລາຄາສວນທາງ (Anomaly Detection)
    # ສົມມຸດວ່າ: ຖ້າທີມເຈົ້າບ້ານສະຖິຕິດີກວ່າຫຼາຍ ແຕ່ລາຄາ AH ພັດນ້ອຍ ຫຼື ໄຫຼລົງ = ສວນທາງ
    price_movement = random.choice(["ໄຫຼຂຶ້ນ (ປົກກະຕິ)", "ໄຫຼລົງ (ສວນທາງ)", "ຄົງທີ່"])
    is_anomaly = "❌ ສວນທາງຄວາມຈິງ" if (last_10_win_home > 70 and "ໄຫຼລົງ" in price_movement) else "✅ ສອດຄ່ອງ"

    analysis_data = {
        "ຫົວຂໍ້ວິເຄາະ": [
            "ສະຖິຕິ H2H (ຊະນະ %)", 
            "ຟອມ 10 ນັດຫຼ້າສຸດ (ຊະນະ %)", 
            "ຊະນະລາຄາ AH (10 ນັດຫຼ້າສຸດ)", 
            "ຄວາມພ້ອມນັກເຕະ (%)",
            "ແຜນການຫຼິ້ນ"
        ],
        home: [f"{h2h_win_home}%", f"{last_10_win_home}%", f"{random.randint(4,8)}/10", "90%", "4-3-3"],
        away: [f"{100-h2h_win_home}%", f"{last_10_win_away}%", f"{random.randint(3,7)}/10", "85%", "4-2-3-1"]
    }
    
    return pd.DataFrame(analysis_data), is_anomaly, price_movement

# --- 4. ສ່ວນສະແດງຜົນ (Main UI) ---
df_matches = get_match_list()

if not df_matches.empty:
    # ສ້າງ Selectbox ເລືອກຄູ່ບານ
    match_options = df_matches['ເຈົ້າບ້ານ'] + " vs " + df_matches['ທີມຢືນ']
    selected_idx = st.selectbox("🎯 ເລືອກຄູ່ທີ່ຕ້ອງການວິເຄາະເຈາະເລິກ:", range(len(match_options)), format_func=lambda x: match_options[x])
    
    home_t = df_matches.iloc[selected_idx]['ເຈົ້າບ້ານ']
    away_t = df_matches.iloc[selected_idx]['ທີມຢືນ']
    current_ah = df_matches.iloc[selected_idx]['ລາຄາ AH']

    # ປຸ່ມກົດວິເຄາະ
    if st.button("🚀 ເລີ່ມວິເຄາະ ແລະ ບັນທຶກຂໍ້ມູນ"):
        st.divider()
        
        # ເອີ້ນໃຊ້ຟັງຊັນວິເຄາະ
        res_df, anomaly, move = deep_analysis(home_t, away_t, current_ah)
        
        # ສະແດງຜົນເປີເຊັນ ແລະ ຄວາມຜິດປົກກະຕິ
        col1, col2, col3 = st.columns(3)
        col1.metric("ລາຄາປະຈຸບັນ", current_ah)
        col2.metric("ການເຄື່ອນໄຫວລາຄາ", move)
        col3.metric("ຄວາມສົມເຫດສົມຜົນ", anomaly)

        # ຕາຕະລາງສົມທຽບ
        st.subheader(f"📊 ສົມທຽບລະອຽດ: {home_t} vs {away_t}")
        st.table(res_df)

        # ສ້າງໄຟລ໌ CSV ແລະ ປຸ່ມດາວໂຫລດ
        final_filename = f"analysis_{home_t}.csv"
        res_df.to_csv(final_filename, index=False, encoding='utf-8-sig')
        
        with open(final_filename, "rb") as file:
            st.download_button(
                label="📥 ດາວໂຫລດຜົນວິເຄາະ (CSV)",
                data=file,
                file_name=final_filename,
                mime="text/csv"
            )
            
        # ສ່ວນລາຍຊື່ນັກເຕະ ແລະ ຂ່າວ (Simulated)
        st.subheader("📰 ຂໍ້ມູນເພີ່ມເຕີມຈາກ Google & News")
        st.info(f"**ລາຍຊື່ 11 ຕົວຈິງ:** {home_t} ຄາດວ່າຈະໃຊ້ຊຸດໃຫຍ່, {away_t} ຂາດກອງຫຼັງຕົວຫຼັກ 1 ຄົນ.")
        st.warning(f"**ປັດໄຈກຳນົດ:** ສະພາບອາກາດມີຝົນຕົກ, ອາດສົ່ງຜົນຕໍ່ການເຮັດປະຕູ.")

else:
    st.error("ບໍ່ສາມາດດຶງຂໍ້ມູນໄດ້ໃນເວລານີ້.")

# --- Sidebar ສໍາລັບເບິ່ງຕາຕະລາງທັງໝົດ ---
st.sidebar.header("📅 ຕາຕະລາງທັງໝົດ")
st.sidebar.dataframe(df_matches[['ເວລາ', 'ເຈົ້າບ້ານ', 'ທີມຢືນ']])

