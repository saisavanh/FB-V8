import re
import math
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="V22 LIVE AI", page_icon="⚽", layout="wide")

URL = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
}

def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()

def fetch_html(cookie=""):
    h = HEADERS.copy()
    if cookie.strip():
        h["Cookie"] = cookie.strip()
    r = requests.get(URL, headers=h, timeout=30)
    return r.status_code, r.text, dict(r.headers)

def parse_goal7(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    league = ""

    for tr in soup.find_all("tr"):
        txt = clean(tr.get_text(" ", strip=True))
        tds = tr.find_all("td")
        ths = tr.find_all("th")

        if ths and len(txt) > 5:
            league = txt
            continue

        if len(tds) < 6:
            if any(k in txt.lower() for k in ["league", "liga", "cup", "bundesliga", "serie"]):
                league = txt
            continue

        cols = [clean(td.get_text(" ", strip=True)) for td in tds]

        item = {
            "ລີກ": league,
            "ເວລາ": cols[0] if len(cols) > 0 else "",
            "ສົດ": cols[2] if len(cols) > 2 else "",
            "ເຈົ້າບ້ານ": cols[3] if len(cols) > 3 else "",
            "ລາຄາ": cols[4] if len(cols) > 4 else "",
            "ທີມຢາມ": cols[5] if len(cols) > 5 else "",
            "ຄຶ່ງແຮກ": cols[6] if len(cols) > 6 else "",
            "ຜົນ": cols[7] if len(cols) > 7 else "",
            "ວິເຄາະ": cols[8] if len(cols) > 8 else "",
            "raw": " | ".join(cols),
        }

        if item["ເຈົ້າບ້ານ"] and item["ທີມຢາມ"]:
            rows.append(item)

    return pd.DataFrame(rows)

def score_ai(row):
    raw = clean(row.get("raw", "")) + " " + clean(row.get("ລາຄາ", ""))
    price_nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", raw)[:8]]

    home_score = 50
    away_score = 50

    if price_nums:
        avg = sum(price_nums) / len(price_nums)
        if avg < 0:
            home_score += 8
        elif avg > 0:
            away_score += 8

    if "ต่อ" in raw or "ต" in raw:
        home_score += 3
    if "รอง" in raw:
        away_score += 3

    total = home_score + away_score
    hp = home_score / total * 100
    ap = away_score / total * 100

    if hp >= ap:
        pick = "ເຈົ້າບ້ານ"
        conf = hp
    else:
        pick = "ທີມຢາມ"
        conf = ap

    ou = "ສູງ" if len(raw) % 2 == 0 else "ຕ່ຳ"
    value = conf

    if price_nums:
        value += 10
    if conf >= 55:
        value += 8

    value = min(99, round(value, 2))

    if value >= 80:
        level = "🔥 ຄູ່ເດັດ"
        alert = "ແຈ້ງເຕືອນແຮງ"
    elif value >= 70:
        level = "✅ ນ່າຫຼິ້ນ"
        alert = "ແຈ້ງເຕືອນ"
    elif value >= 60:
        level = "🟡 ພໍເບິ່ງ"
        alert = "ລໍຖ້າ"
    else:
        level = "⚠️ ຂ້າມ"
        alert = "ບໍ່ແນະນຳ"

    return pd.Series({
        "AI_ຝັ່ງ": pick,
        "AI_%": round(conf, 2),
        "OU": ou,
        "Value_%": value,
        "ລະດັບ": level,
        "Alert": alert,
    })

def add_ai(df):
    if df.empty:
        return df
    ai = df.apply(score_ai, axis=1)
    out = pd.concat([df.reset_index(drop=True), ai], axis=1)
    return out.sort_values(["Value_%", "AI_%"], ascending=False)

st.title("⚽ V22 LIVE AI + ALERT")
st.caption("ດຶງຕາຕະລາງ goal7 + AI + Value Bet + Alert")

cookie = st.text_area("Cookie ຖ້າຈຳເປັນ", height=90)
auto = st.checkbox("Auto refresh 60 ວິນາທີ", value=False)
show_debug = st.checkbox("Debug", value=False)

if auto:
    st.markdown("<meta http-equiv='refresh' content='60'>", unsafe_allow_html=True)

if st.button("🚀 ດຶງຂໍ້ມູນ V22", use_container_width=True):
    status, html, headers = fetch_html(cookie)

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", status)
    c2.metric("Size", len(html))
    c3.metric("Type", headers.get("content-type", "-"))

    if status != 200:
        st.error("ດຶງບໍ່ໄດ້ — Cookie ຫຼື Cloudflare ອາດມີບັນຫາ")
        st.stop()

    df = parse_goal7(html)
    final = add_ai(df)

    if final.empty:
        st.warning("ບໍ່ພົບຕາຕະລາງ")
        st.code(html[:2000])
        st.stop()

    st.success(f"ດຶງໄດ້ {len(final)} ຄູ່")

    st.subheader("🔥 5 ຄູ່ເດັດ V22")
    st.dataframe(final.head(5), use_container_width=True)

    st.subheader("🚨 Alert")
    alerts = final[final["Value_%"] >= 70]
    st.dataframe(alerts, use_container_width=True)

    st.subheader("📊 ຕາຕະລາງທັງໝົດ")
    st.dataframe(final, use_container_width=True)

    csv = final.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ ດາວໂຫຼດ CSV", csv, "v22_live_ai.csv", "text/csv", use_container_width=True)

    if show_debug:
        st.subheader("Debug HTML")
        st.code(html[:3000])
