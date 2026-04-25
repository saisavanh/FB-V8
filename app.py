import re
import os
import sqlite3
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="V29 REAL AI", page_icon="⚽", layout="wide")

BASE = "https://goal7.co"
PAGE_URL = BASE + "/ตารางบอลวันนี้/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": BASE + "/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
}

DATA_DIR = "data_store"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "v29_real_ai.sqlite")
CSV_PATH = os.path.join(DATA_DIR, "latest_v29.csv")

def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()

def fetch(url, cookie=""):
    h = HEADERS.copy()
    if cookie.strip():
        h["Cookie"] = cookie.strip()
    try:
        r = requests.get(url, headers=h, timeout=30)
        return r.status_code, r.text, r.url
    except Exception as e:
        return 0, str(e), url

def parse_ah(price):
    price = clean(price)
    if "เสมอ" in price:
        return 0.0
    nums = re.findall(r"-?\d+(?:\.\d+)?", price)
    if not nums:
        return 0.0
    try:
        return float(nums[0])
    except:
        return 0.0

def is_team(x):
    x = clean(x)
    return "[" in x and "]" in x and len(x) < 90

def is_price(x):
    x = clean(x)
    return any(k in x for k in ["0/0.5", "0.5", "1/1.5", "1.5", "2.5", "เสมอ", "/", "-"])

def parse_main_page(html):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    league = ""

    for tr in soup.find_all("tr"):
        cols = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        text = " | ".join(cols)

        if len(cols) < 5:
            if any(k in text.lower() for k in ["league", "liga", "cup", "serie", "premier", "bundesliga", "championship"]):
                league = text
            continue

        teams = [c for c in cols if is_team(c)]
        prices = [c for c in cols if is_price(c)]

        links = []
        for a in tr.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = BASE + href
            links.append(href)

        analyse = next((x for x in links if "analyse" in x), "")

        if len(teams) >= 2:
            rows.append({
                "ລີກ": league,
                "ເວລາ": cols[0] if cols else "",
                "ເຈົ້າບ້ານ": teams[0],
                "ທີມຢາມ": teams[1],
                "ລາຄາ_AH": prices[0] if prices else "",
                "ຜົນ_live": next((c for c in cols if re.search(r"\d+\s*-\s*\d+|\?\s*-\s*\?", c)), ""),
                "analyse_link": analyse,
                "raw": text,
            })

    return pd.DataFrame(rows)

def analyse_page(url, cookie=""):
    result = {"games": 0, "wins": 0, "draws": 0, "losses": 0, "avg_goal": 0.0, "h2h": 0}

    if not url:
        return result

    status, html, _ = fetch(url, cookie)
    if status != 200:
        return result

    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    scores = re.findall(r"(\d+)\s*-\s*(\d+)", text)

    goals = []
    for h, a in scores[:20]:
        h, a = int(h), int(a)
        goals.append(h + a)
        if h > a:
            result["wins"] += 1
        elif h == a:
            result["draws"] += 1
        else:
            result["losses"] += 1

    result["games"] = len(scores[:20])
    result["h2h"] = len(scores)
    result["avg_goal"] = round(sum(goals) / len(goals), 2) if goals else 0.0
    return result

def ai_engine(row):
    ah = parse_ah(row.get("ລາຄາ_AH", ""))
    raw = clean(row.get("raw", ""))
    avg_goal = float(row.get("avg_goal", 0) or 0)
    wins = float(row.get("wins", 0) or 0)
    losses = float(row.get("losses", 0) or 0)
    h2h = float(row.get("h2h", 0) or 0)

    home = 52.0
    away = 48.0
    reason = ["ເຈົ້າບ້ານໄດ້ home advantage"]

    if ah < 0:
        home += abs(ah) * 18
        reason.append("AH ໄປທາງເຈົ້າບ້ານ")
    elif ah > 0:
        away += abs(ah) * 18
        reason.append("AH ໄປທາງທີມຢາມ")
    else:
        reason.append("AH ເສມອ")

    form = wins - losses
    if form > 0:
        home += form * 2.5
        reason.append("ຟອມຈາກ analyse ດີ")
    elif form < 0:
        away += abs(form) * 2.5
        reason.append("ຟອມຈາກ analyse ໄປທາງທີມຢາມ")

    if "ต่อ" in raw:
        home += 7
        reason.append("ຂໍ້ຄວາມມີຝັ່ງຕໍ່")
    if "รอง" in raw:
        away += 7
        reason.append("ຂໍ້ຄວາມມີຝັ່ງຮອງ")

    total = home + away
    hp = home / total * 100
    ap = away / total * 100

    pick = "ເຈົ້າບ້ານ" if hp >= ap else "ທີມຢາມ"
    conf = max(hp, ap)

    ou = "ສູງ" if avg_goal >= 2.5 else "ຕ່ຳ"
    ou_percent = 65 if avg_goal >= 2.5 else 58

    value = conf
    if abs(ah) >= 1:
        value += 10
    elif abs(ah) >= 0.5:
        value += 6
    if h2h > 0:
        value += 5
    if avg_goal > 0:
        value += 4

    value = min(99, round(value, 2))

    if value >= 85:
        alert = "🚨 STRONG"
        level = "🔥 ຄູ່ເດັດ"
    elif value >= 75:
        alert = "⚠️ BET"
        level = "✅ ນ່າຫຼິ້ນ"
    elif value >= 65:
        alert = "📊 WATCH"
        level = "🟡 ເບິ່ງໄດ້"
    else:
        alert = "—"
        level = "❌ ຂ້າມ"

    return pd.Series({
        "AI_ຝັ່ງ": pick,
        "AI_%": round(conf, 2),
        "AH": ah,
        "OU": ou,
        "OU_%": ou_percent,
        "Value_%": value,
        "ຄວາມໝັ້ນໃຈ_%": value,
        "ລະດັບ": level,
        "Alert": alert,
        "ເຫດຜົນ": " | ".join(reason)
    })

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pulled_at TEXT,
            league TEXT,
            time TEXT,
            home TEXT,
            away TEXT,
            price TEXT,
            live_score TEXT,
            analyse_link TEXT,
            ai_pick TEXT,
            ai_percent REAL,
            value_percent REAL,
            alert TEXT,
            reason TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_data(df):
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, r in df.iterrows():
        conn.execute("""
            INSERT INTO snapshots
            (pulled_at, league, time, home, away, price, live_score, analyse_link,
             ai_pick, ai_percent, value_percent, alert, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            str(r.get("ລີກ", "")),
            str(r.get("ເວລາ", "")),
            str(r.get("ເຈົ້າບ້ານ", "")),
            str(r.get("ທີມຢາມ", "")),
            str(r.get("ລາຄາ_AH", "")),
            str(r.get("ຜົນ_live", "")),
            str(r.get("analyse_link", "")),
            str(r.get("AI_ຝັ່ງ", "")),
            float(r.get("AI_%", 0) or 0),
            float(r.get("Value_%", 0) or 0),
            str(r.get("Alert", "")),
            str(r.get("ເຫດຜົນ", ""))
        ))
    conn.commit()
    conn.close()

def load_latest():
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame()

def load_history():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY id DESC LIMIT 300", conn)
    conn.close()
    return df

st.title("⚽ V29 REAL AI")
st.caption("ດຶງຕາຕະລາງ + analyse link + ສະຖິຕິ + AI % ບໍ່ random + ບັນທຶກ file")

init_db()

tab1, tab2 = st.tabs(["🔥 LIVE", "📂 FILE"])

with tab1:
    cookie = st.text_area("Cookie ຖ້າຈຳເປັນ", height=80)
    limit = st.number_input("ຈຳນວນຄູ່ທີ່ເຂົ້າ analyse", 0, 80, 15)
    debug = st.checkbox("Debug", value=False)

    if st.button("🚀 RUN V29 REAL AI", use_container_width=True):
        status, html, final_url = fetch(PAGE_URL, cookie)

        st.write("Status:", status)
        if status != 200:
            st.error("ດຶງບໍ່ໄດ້")
            st.stop()

        df = parse_main_page(html)

        if df.empty:
            st.error("ບໍ່ພົບຕາຕະລາງ")
            if debug:
                st.code(html[:3000])
            st.stop()

        deep_rows = []
        for i, row in df.iterrows():
            deep = {"games": 0, "wins": 0, "draws": 0, "losses": 0, "avg_goal": 0.0, "h2h": 0}
            if i < int(limit):
                deep = analyse_page(row.get("analyse_link", ""), cookie)

            full = row.to_dict()
            full.update(deep)
            deep_rows.append(full)

        final = pd.DataFrame(deep_rows)
        ai_df = final.apply(ai_engine, axis=1)
        final = pd.concat([final.reset_index(drop=True), ai_df], axis=1)
        final = final.sort_values(["Value_%", "AI_%"], ascending=False)

        save_data(final)

        st.success(f"ດຶງໄດ້ {len(final)} ຄູ່ ແລະບັນທຶກ file ແລ້ວ")

        st.subheader("🔥 TOP 5 ຄູ່ເດັດ")
        st.dataframe(final.head(5), use_container_width=True)

        st.subheader("🚨 SIGNAL")
        st.dataframe(final[final["Alert"] != "—"], use_container_width=True)

        st.subheader("📊 ທັງໝົດ")
        st.dataframe(final, use_container_width=True)

        csv = final.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV", csv, "v29_real_ai.csv", "text/csv", use_container_width=True)

with tab2:
    st.subheader("📂 latest_v29.csv")
    st.dataframe(load_latest(), use_container_width=True)

    st.subheader("🕘 SQLite History")
    st.dataframe(load_history(), use_container_width=True)
