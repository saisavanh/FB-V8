import re
import json
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="V12 REAL API", layout="wide")

URL = "https://goal7.co/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# STEP 1: ดึง HTML
# =========================
def get_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.text
    except:
        return ""

# =========================
# STEP 2: หา API hidden
# =========================
def find_api(html):
    patterns = [
        r'https://[^"]+api[^"]+',
        r'https://[^"]+match[^"]+',
        r'https://[^"]+odds[^"]+',
        r'https://[^"]+json[^"]+',
    ]

    apis = []
    for p in patterns:
        found = re.findall(p, html)
        apis.extend(found)

    return list(set(apis))

# =========================
# STEP 3: ยิง API
# =========================
def fetch_api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        return None

# =========================
# STEP 4: parse match จริง
# =========================
def parse_matches(data):
    rows = []

    if isinstance(data, dict):
        data = [data]

    for block in data:
        if not isinstance(block, dict):
            continue

        home = block.get("home") or block.get("homeTeam") or "-"
        away = block.get("away") or block.get("awayTeam") or "-"

        odds = block.get("odds", {})

        rows.append({
            "home": home,
            "away": away,
            "1": odds.get("home", 0),
            "X": odds.get("draw", 0),
            "2": odds.get("away", 0),
            "AH": odds.get("ah", "-"),
            "O/U": odds.get("ou", "-"),
        })

    return rows

# =========================
# UI
# =========================
st.title("⚽ Football AI V12 (REAL API MODE)")

if st.button("🚀 ดึงข้อมูลจริง"):
    html = get_html(URL)

    if not html:
        st.error("❌ โหลดเว็บไม่ได้")
    else:
        apis = find_api(html)

        st.subheader("🔍 API ที่เจอ")
        st.write(apis)

        all_rows = []

        for api in apis[:5]:  # จำกัด
            data = fetch_api(api)

            if data:
                rows = parse_matches(data)
                all_rows.extend(rows)

        if all_rows:
            df = pd.DataFrame(all_rows)
            st.success(f"✅ เจอ {len(df)} คู่")
            st.dataframe(df)
        else:
            st.warning("⚠️ ยัง parse ไม่ได้ (ต้องปรับ API)")
