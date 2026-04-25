import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")
st.title("⚽ GOAL7 GOD MODE V28")

BASE_URL = "https://goal7.co"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# DATA STORAGE
# =========================
DATA_DIR = "data_store"
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "football.sqlite")
CSV_PATH = os.path.join(DATA_DIR, "latest.csv")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pulled_at TEXT,
        league TEXT,
        time TEXT,
        home TEXT,
        away TEXT,
        price TEXT,
        score TEXT,
        analyse TEXT,
        ai TEXT,
        ai_percent REAL,
        value_percent REAL
    )
    """)

    conn.commit()
    conn.close()

# =========================
# SCRAPER MAIN PAGE
# =========================
def fetch_matches():
    url = BASE_URL + "/ตารางบอลวันนี้/"
    res = requests.get(url, headers=HEADERS, timeout=10)

    soup = BeautifulSoup(res.text, "html.parser")

    rows = []

    table = soup.find_all("tr")

    for tr in table:
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue

        try:
            time = tds[0].get_text(strip=True)
            home = tds[2].get_text(strip=True)
            away = tds[3].get_text(strip=True)
            price = tds[1].get_text(strip=True)

            link_tag = tr.find("a", href=True)
            analyse_link = BASE_URL + link_tag["href"] if link_tag else ""

            rows.append({
                "time": time,
                "home": home,
                "away": away,
                "price": price,
                "analyse": analyse_link
            })
        except:
            continue

    return pd.DataFrame(rows)

# =========================
# SCRAPER ANALYSE PAGE
# =========================
def fetch_analyse(url):
    if not url:
        return {}

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text()

        # logic dummy (upgrade later)
        form = np.random.uniform(0.4, 0.9)
        h2h = np.random.uniform(0.4, 0.9)
        goal = np.random.uniform(1.5, 3.5)

        return {
            "form": form,
            "h2h": h2h,
            "goal": goal
        }
    except:
        return {
            "form": 0,
            "h2h": 0,
            "goal": 0
        }

# =========================
# AI ENGINE
# =========================
def calculate_ai(row):
    score = (row["form"]*0.4 + row["h2h"]*0.3 + row["goal"]*0.3)

    percent = int(score * 100)

    if percent > 60:
        pick = "ເຈົ້າບ້ານ"
    elif percent < 40:
        pick = "ທີມຢາມ"
    else:
        pick = "ສະເໝີ"

    value = abs(percent - 50)

    return pick, percent, value

# =========================
# SAVE DATA
# =========================
def save_data(df):
    df.to_csv(CSV_PATH, index=False)

    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, r in df.iterrows():
        conn.execute("""
        INSERT INTO matches
        (pulled_at, league, time, home, away, price, score, analyse, ai, ai_percent, value_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            "",
            r["time"],
            r["home"],
            r["away"],
            r["price"],
            "",
            r["analyse"],
            r["AI"],
            r["AI_%"],
            r["Value_%"]
        ))

    conn.commit()
    conn.close()

# =========================
# LOAD
# =========================
def load_csv():
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame()

def load_db():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM matches ORDER BY id DESC LIMIT 200", conn)
    conn.close()
    return df

# =========================
# RUN
# =========================
init_db()

tab1, tab2 = st.tabs(["🔥 LIVE", "📂 FILE"])

with tab1:
    if st.button("🚀 RUN SCRAPER + AI"):
        df = fetch_matches()

        results = []

        for _, r in df.iterrows():
            analyse = fetch_analyse(r["analyse"])

            row = {
                **r,
                **analyse
            }

            ai, percent, value = calculate_ai(row)

            row["AI"] = ai
            row["AI_%"] = percent
            row["Value_%"] = value

            results.append(row)

        final = pd.DataFrame(results)

        st.success("✅ DONE")

        st.subheader("🔥 TOP 5")
        st.dataframe(final.sort_values("Value_%", ascending=False).head(5))

        st.subheader("📊 ALL MATCHES")
        st.dataframe(final)

        save_data(final)

with tab2:
    st.subheader("📂 CSV DATA")
    st.dataframe(load_csv())

    st.subheader("🕘 HISTORY DB")
    st.dataframe(load_db())
