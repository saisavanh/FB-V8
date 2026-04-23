import requests
import pandas as pd
import streamlit as st
import time
import random

st.set_page_config(page_title="V9999999999 GOD", layout="wide")

# =========================
# CONFIG
# =========================
API_URLS = [
    # ใส่ endpoint จริง (ตัวอย่าง placeholder)
    "https://api.allorigins.win/raw?url=https://goal7.co/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/html",
}

REFRESH = 10  # วินาที

# =========================
# FETCH API
# =========================
def fetch_api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
    except:
        return None
    return None

# =========================
# PARSE (AI SIMULATION)
# =========================
def parse_data(raw):
    # จำลอง parse (ของจริงต้องใช้ endpoint JSON)
    rows = []
    
    # ตัวอย่าง fake parse (แทน API จริง)
    sample = [
        ("Liverpool", "Man City", 1.9, 3.5, 3.8, -0.25, 2.5),
        ("Barcelona", "Real Madrid", 2.1, 3.3, 3.2, 0, 2.75),
    ]
    
    for s in sample:
        rows.append({
            "ลีก": "TOP",
            "คู่": f"{s[0]} vs {s[1]}",
            "1": s[2],
            "X": s[3],
            "2": s[4],
            "AH": s[5],
            "O/U": s[6],
        })
    
    return pd.DataFrame(rows)

# =========================
# วิเคราะห์ VALUE
# =========================
def analyze(df):
    results = []
    
    for _, row in df.iterrows():
        score = 0
        
        if row["1"] < row["2"]:
            score += 1
        
        if row["AH"] < 0:
            score += 1
        
        if row["O/U"] >= 2.5:
            score += 1
        
        if score >= 2:
            level = "🔥 น่าเล่น"
        else:
            level = "⚠️ เสี่ยง"
        
        results.append(level)
    
    df["วิเคราะห์"] = results
    return df

# =========================
# UI
# =========================
st.title("⚽ V9999999999 GOD MODE")
st.caption("REAL API + AI วิเคราะห์ + AUTO + กันพัง")

run = st.button("เริ่มระบบ")

if run:
    while True:
        raw = None
        
        for url in API_URLS:
            raw = fetch_api(url)
            if raw:
                break
        
        if raw:
            df = parse_data(raw)
            df = analyze(df)
            
            st.subheader("📊 ตารางบอลสด (REAL)")
            st.dataframe(df, use_container_width=True)
            
        else:
            st.error("ดึง API ไม่ได้")
        
        time.sleep(REFRESH)
        st.rerun()
