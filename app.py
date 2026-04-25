import re
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(layout="wide")

BASE = "https://goal7.co"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": BASE
}

# --------------------------
# 🔹 ดึงหน้า analyse
# --------------------------
def fetch_analyse(url, cookie=""):
    try:
        h = HEADERS.copy()
        if cookie:
            h["Cookie"] = cookie

        r = requests.get(url, headers=h, timeout=15)
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, "lxml")

        txt = soup.get_text(" ", strip=True)

        # ----------------------
        # 🔥 ดึงฟอร์ม 10 นัด
        # ----------------------
        wins = len(re.findall(r"\bW\b", txt))
        draws = len(re.findall(r"\bD\b", txt))
        loses = len(re.findall(r"\bL\b", txt))

        # ----------------------
        # 🔥 ดึง H2H
        # ----------------------
        h2h = len(re.findall(r"\d+\s*-\s*\d+", txt))

        # ----------------------
        # 🔥 ดึงค่าเฉลี่ยประตู
        # ----------------------
        scores = re.findall(r"(\d+)\s*-\s*(\d+)", txt)
        goals = []
        for s in scores[:10]:
            goals.append(int(s[0]) + int(s[1]))

        avg_goal = sum(goals)/len(goals) if goals else 0

        return {
            "W": wins,
            "D": draws,
            "L": loses,
            "H2H": h2h,
            "AVG_GOAL": avg_goal
        }

    except:
        return {}

# --------------------------
# 🔹 วิเคราะห์ AI จริง
# --------------------------
def ai_deep(row, analyse):
    base = 50
    home = base
    away = base
    reason = []

    # 🔥 AH
    ah = row.get("AH", 0)
    if ah < 0:
        home += abs(ah) * 20
        reason.append("AH ເຈົ້າບ້ານແຂງ")
    elif ah > 0:
        away += abs(ah) * 20
        reason.append("AH ທີມຢາມແຂງ")

    # 🔥 วิเคราะห์จาก analyse page
    if analyse:
        form_score = analyse["W"] - analyse["L"]

        if form_score > 0:
            home += form_score * 3
            reason.append("ຟອມດີ")
        else:
            away += abs(form_score) * 3
            reason.append("ຟອມອ່ອນ")

        # 🔥 H2H
        if analyse["H2H"] >= 5:
            home += 5
            reason.append("H2H ຫຼາຍ")

        # 🔥 Goals
        if analyse["AVG_GOAL"] > 2.5:
            ou = "ສູງ"
        else:
            ou = "ຕ່ຳ"
    else:
        ou = "ບໍ່ຮູ້"

    total = home + away
    hp = home / total * 100
    ap = away / total * 100

    pick = "ເຈົ້າບ້ານ" if hp > ap else "ທີມຢາມ"
    conf = max(hp, ap)

    return pd.Series({
        "AI_ຝັ່ງ": pick,
        "AI_%": round(conf, 2),
        "OU": ou,
        "Value_%": round(conf, 2),
        "ເຫດຜົນ": " | ".join(reason)
    })

# --------------------------
# 🔹 main UI
# --------------------------
st.title("🔥 V26 PRO MAX (Deep Analyse)")

cookie = st.text_area("Cookie", "")

if st.button("🚀 RUN AI REAL"):
    url = BASE + "/ตารางบอลวันนี้/"

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "lxml")

    rows = []

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue

        cols = [td.get_text(strip=True) for td in tds]

        # 🔥 หา analyse link
        analyse_link = ""
        for a in tr.find_all("a", href=True):
            if "analyse" in a["href"]:
                analyse_link = BASE + a["href"]

        rows.append({
            "home": cols[3] if len(cols) > 3 else "",
            "away": cols[5] if len(cols) > 5 else "",
            "price": cols[4] if len(cols) > 4 else "",
            "analyse": analyse_link
        })

    df = pd.DataFrame(rows)

    st.success(f"ດຶງໄດ້ {len(df)} ຄູ່")

    results = []

    # 🔥 loop วิเคราะห์จริง
    for i, row in df.iterrows():
        analyse_data = {}

        if row["analyse"]:
            analyse_data = fetch_analyse(row["analyse"], cookie)
            time.sleep(1)  # กันโดน block

        ai = ai_deep(row, analyse_data)

        results.append({
            "ເຈົ້າບ້ານ": row["home"],
            "ທີມຢາມ": row["away"],
            "AI": ai["AI_ຝັ່ງ"],
            "AI_%": ai["AI_%"],
            "OU": ai["OU"],
            "Value_%": ai["Value_%"],
            "ເຫດຜົນ": ai["ເຫດຜົນ"]
        })

    final = pd.DataFrame(results).sort_values("Value_%", ascending=False)

    st.subheader("🔥 TOP 5 ຄູ່ເດັດ")
    st.dataframe(final.head(5), use_container_width=True)

    st.subheader("📊 ທັງໝົດ")
    st.dataframe(final, use_container_width=True)
