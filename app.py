import re
import os
import json
import math
import sqlite3
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="V31 FULL AI LOGIC", page_icon="⚽", layout="wide")

BASE = "https://goal7.co"
PAGE_URL = BASE + "/ตารางบอลวันนี้/"

DATA_DIR = "data_store"
os.makedirs(DATA_DIR, exist_ok=True)

JSON_FILE = os.path.join(DATA_DIR, "v31_latest.json")
CSV_FILE = os.path.join(DATA_DIR, "v31_latest.csv")
DB_FILE = os.path.join(DATA_DIR, "v31_history.sqlite")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": BASE + "/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
}

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

def is_team(x):
    x = clean(x)
    return "[" in x and "]" in x and len(x) <= 90

def is_price(x):
    x = clean(x)
    return any(k in x for k in ["0/0.5", "0.5", "1/1.5", "1.5", "2.5", "เสมอ", "/", "-"])

def parse_ah(price):
    p = clean(price)
    if "เสมอ" in p:
        return 0.0
    nums = re.findall(r"-?\d+(?:\.\d+)?", p)
    try:
        return float(nums[0]) if nums else 0.0
    except:
        return 0.0

def parse_main_page(html):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    league = ""

    for tr in soup.find_all("tr"):
        cols = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        raw = " | ".join(cols)

        if len(cols) < 5:
            if any(k in raw.lower() for k in ["league", "liga", "cup", "serie", "premier", "bundesliga", "championship"]):
                league = raw
            continue

        teams = [c for c in cols if is_team(c)]
        prices = [c for c in cols if is_price(c)]

        links = []
        for a in tr.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = BASE + href
            links.append(href)

        analyse_link = next((x for x in links if "analyse" in x), "")

        if len(teams) >= 2:
            rows.append({
                "ລີກ": league,
                "ເວລາ": cols[0] if cols else "",
                "ເຈົ້າບ້ານ": teams[0],
                "ທີມຢາມ": teams[1],
                "ລາຄາ_AH": prices[0] if prices else "",
                "ຜົນ_live": next((c for c in cols if re.search(r"\d+\s*-\s*\d+|\?\s*-\s*\?", c)), ""),
                "analyse_link": analyse_link,
                "raw": raw,
            })

    return pd.DataFrame(rows)

def analyse_page(url, cookie=""):
    out = {
        "games": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "avg_goal": 0.0,
        "h2h": 0,
        "goals_for_avg": 0.0,
        "goals_against_avg": 0.0,
    }

    if not url:
        return out

    status, html, _ = fetch(url, cookie)
    if status != 200:
        return out

    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    scores = re.findall(r"(\d+)\s*-\s*(\d+)", text)

    goals_for, goals_against, total_goals = [], [], []

    for h, a in scores[:20]:
        h, a = int(h), int(a)
        goals_for.append(h)
        goals_against.append(a)
        total_goals.append(h + a)

        if h > a:
            out["wins"] += 1
        elif h == a:
            out["draws"] += 1
        else:
            out["losses"] += 1

    out["games"] = len(scores[:20])
    out["h2h"] = len(scores)
    out["avg_goal"] = round(sum(total_goals) / len(total_goals), 2) if total_goals else 0.0
    out["goals_for_avg"] = round(sum(goals_for) / len(goals_for), 2) if goals_for else 0.0
    out["goals_against_avg"] = round(sum(goals_against) / len(goals_against), 2) if goals_against else 0.0
    return out

def poisson_prob(lam, k):
    lam = max(float(lam), 0.01)
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def poisson_match(home_lambda, away_lambda, max_goals=6):
    home_win = draw = away_win = over25 = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_prob(home_lambda, h) * poisson_prob(away_lambda, a)
            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p
            if h + a >= 3:
                over25 += p

    return {
        "home_win_%": round(home_win * 100, 2),
        "draw_%": round(draw * 100, 2),
        "away_win_%": round(away_win * 100, 2),
        "over25_%": round(over25 * 100, 2),
        "under25_%": round((1 - over25) * 100, 2),
    }

def sign_logic_score(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0

def demand_supply_logic(ah, raw):
    demand = 50.0
    supply = 50.0

    if "ต่อ" in raw:
        demand += 12
    if "รอง" in raw:
        supply += 12

    if ah < 0:
        demand += abs(ah) * 18
    elif ah > 0:
        supply += abs(ah) * 18

    gap = demand - supply
    return demand, supply, gap

def advanced_logic_score(ah, form, avg_goal, h2h, raw):
    sign_ah = sign_logic_score(-ah)
    sign_form = sign_logic_score(form)
    sign_goal = sign_logic_score(avg_goal - 2.5)
    sign_h2h = sign_logic_score(h2h - 5)

    logic_power = (
        sign_ah * 30 +
        sign_form * 25 +
        sign_goal * 20 +
        sign_h2h * 15
    )

    if "ต่อ" in raw:
        logic_power += 10
    if "รอง" in raw:
        logic_power -= 10

    return logic_power

def multiply_sign_explain(a, b):
    sa = sign_logic_score(a)
    sb = sign_logic_score(b)
    result = sa * sb
    if result > 0:
        return "+"
    if result < 0:
        return "-"
    return "0"

def analysis_engine(row):
    ah = parse_ah(row.get("ລາຄາ_AH", ""))
    raw = clean(row.get("raw", ""))

    games = float(row.get("games", 0) or 0)
    wins = float(row.get("wins", 0) or 0)
    draws = float(row.get("draws", 0) or 0)
    losses = float(row.get("losses", 0) or 0)
    avg_goal = float(row.get("avg_goal", 0) or 0)
    h2h = float(row.get("h2h", 0) or 0)
    gf = float(row.get("goals_for_avg", 0) or 0)
    ga = float(row.get("goals_against_avg", 0) or 0)

    form = wins - losses

    if gf <= 0:
        gf = 1.25
    if ga <= 0:
        ga = 1.10
    if avg_goal <= 0:
        avg_goal = 2.35

    home_lambda = max(0.2, (gf * 0.65) + (avg_goal * 0.25) + 0.15)
    away_lambda = max(0.2, (ga * 0.55) + (avg_goal * 0.20))

    if ah < 0:
        home_lambda += abs(ah) * 0.18
    elif ah > 0:
        away_lambda += abs(ah) * 0.18

    if "ต่อ" in raw:
        home_lambda += 0.12
    if "รอง" in raw:
        away_lambda += 0.12

    demand, supply, ds_gap = demand_supply_logic(ah, raw)
    logic_power = advanced_logic_score(ah, form, avg_goal, h2h, raw)

    if ds_gap > 0:
        home_lambda += abs(ds_gap) * 0.01
    elif ds_gap < 0:
        away_lambda += abs(ds_gap) * 0.01

    if logic_power > 0:
        home_lambda += abs(logic_power) * 0.01
    elif logic_power < 0:
        away_lambda += abs(logic_power) * 0.01

    sign_ah_form = multiply_sign_explain(-ah, form)
    sign_goal_h2h = multiply_sign_explain(avg_goal - 2.5, h2h - 5)

    p = poisson_match(home_lambda, away_lambda)

    values = {
        "ເຈົ້າບ້ານໄດ້ປຽບ": p["home_win_%"],
        "ສະເໝີ": p["draw_%"],
        "ທີມຢາມໄດ້ປຽບ": p["away_win_%"],
    }

    result_analysis = max(values, key=values.get)
    advantage = values[result_analysis]

    ou = "ສູງ 2.5" if p["over25_%"] >= p["under25_%"] else "ຕ່ຳ 2.5"
    ou_percent = max(p["over25_%"], p["under25_%"])

    data_quality = 50
    if games >= 10:
        data_quality += 25
    elif games >= 5:
        data_quality += 15
    if clean(row.get("analyse_link", "")):
        data_quality += 10
    if clean(row.get("ລາຄາ_AH", "")):
        data_quality += 10
    if abs(ds_gap) >= 15:
        data_quality += 5
    data_quality = min(95, data_quality)

    confidence = round((advantage * 0.70) + (data_quality * 0.20) + (min(abs(logic_power), 100) * 0.10), 2)

    if confidence >= 70:
        strength = "ຂໍ້ມູນແຂງ"
    elif confidence >= 58:
        strength = "ຂໍ້ມູນປານກາງ"
    else:
        strength = "ຂໍ້ມູນຍັງອ່ອນ"

    reasons = [
        f"Poisson home={round(home_lambda,2)} away={round(away_lambda,2)}",
        f"Home/Draw/Away={p['home_win_%']}%/{p['draw_%']}%/{p['away_win_%']}%",
        f"Demand={round(demand,2)} Supply={round(supply,2)} Gap={round(ds_gap,2)}",
        f"Logic_Power={round(logic_power,2)}",
        f"Sign(AH×Form)={sign_ah_form}",
        f"Sign(Goal×H2H)={sign_goal_h2h}",
        f"OU={ou_percent}%",
        f"analyse={int(games)} ນັດ",
        f"AH={ah}",
    ]

    return pd.Series({
        "ຜົນວິເຄາະ": result_analysis,
        "ຄວາມໄດ້ປຽບ_%": round(advantage, 2),
        "ຄວາມໝັ້ນໃຈ_%": confidence,
        "ຄຸນນະພາບຂໍ້ມູນ_%": data_quality,
        "Home_%": p["home_win_%"],
        "Draw_%": p["draw_%"],
        "Away_%": p["away_win_%"],
        "OU": ou,
        "OU_%": ou_percent,
        "AH": ah,
        "Demand": round(demand, 2),
        "Supply": round(supply, 2),
        "Demand-Supply": round(ds_gap, 2),
        "Logic_Power": round(logic_power, 2),
        "Sign_AH_Form": sign_ah_form,
        "Sign_Goal_H2H": sign_goal_h2h,
        "ລະດັບຂໍ້ມູນ": strength,
        "ເຫດຜົນ": " | ".join(reasons),
    })

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pulled_at TEXT,
            league TEXT,
            match_time TEXT,
            home TEXT,
            away TEXT,
            price_ah TEXT,
            live_score TEXT,
            result_analysis TEXT,
            advantage REAL,
            confidence REAL,
            demand REAL,
            supply REAL,
            logic_power REAL,
            ou TEXT,
            ou_percent REAL,
            reason TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_files(df):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    conn = sqlite3.connect(DB_FILE)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, r in df.iterrows():
        conn.execute("""
            INSERT INTO snapshots (
                pulled_at, league, match_time, home, away, price_ah, live_score,
                result_analysis, advantage, confidence, demand, supply, logic_power,
                ou, ou_percent, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            str(r.get("ລີກ", "")),
            str(r.get("ເວລາ", "")),
            str(r.get("ເຈົ້າບ້ານ", "")),
            str(r.get("ທີມຢາມ", "")),
            str(r.get("ລາຄາ_AH", "")),
            str(r.get("ຜົນ_live", "")),
            str(r.get("ຜົນວິເຄາະ", "")),
            float(r.get("ຄວາມໄດ້ປຽບ_%", 0) or 0),
            float(r.get("ຄວາມໝັ້ນໃຈ_%", 0) or 0),
            float(r.get("Demand", 0) or 0),
            float(r.get("Supply", 0) or 0),
            float(r.get("Logic_Power", 0) or 0),
            str(r.get("OU", "")),
            float(r.get("OU_%", 0) or 0),
            str(r.get("ເຫດຜົນ", ""))
        ))

    conn.commit()
    conn.close()

def load_latest():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame()

def load_history():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY id DESC LIMIT 300", conn)
    conn.close()
    return df

def safe_columns(df, cols):
    return [c for c in cols if c in df.columns]

st.title("⚽ V31 FULL AI LOGIC")
st.caption("Poisson + Demand/Supply + Logic ຂັ້ນສູງ + ຄູນເຄື່ອງໝາຍ +/-")

init_db()

tab_live, tab_file = st.tabs(["🔥 ດຶງຂໍ້ມູນສົດ", "📂 ອ່ານຈາກ file"])

with tab_live:
    cookie = st.text_area("Cookie ຖ້າຈຳເປັນ", height=80)
    limit = st.number_input("ຈຳນວນຄູ່ທີ່ຈະເຂົ້າ analyse", 0, 100, 20)
    debug = st.checkbox("Debug HTML", value=False)

    if st.button("🚀 RUN V31 FULL LOGIC", use_container_width=True):
        status, html, final_url = fetch(PAGE_URL, cookie)
        st.write("Status:", status)

        if status != 200:
            st.error("ດຶງໜ້າ goal7 ບໍ່ໄດ້")
            st.stop()

        main_df = parse_main_page(html)

        if main_df.empty:
            st.error("ບໍ່ພົບຕາຕະລາງ")
            if debug:
                st.code(html[:3000])
            st.stop()

        deep_rows = []
        for i, row in main_df.iterrows():
            deep = {
                "games": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "avg_goal": 0.0,
                "h2h": 0,
                "goals_for_avg": 0.0,
                "goals_against_avg": 0.0,
            }

            if i < int(limit):
                deep = analyse_page(row.get("analyse_link", ""), cookie)

            full = row.to_dict()
            full.update(deep)
            deep_rows.append(full)

        df = pd.DataFrame(deep_rows)
        ana = df.apply(analysis_engine, axis=1)
        final = pd.concat([df.reset_index(drop=True), ana], axis=1)
        final = final.sort_values(["ຄວາມໝັ້ນໃຈ_%", "Logic_Power", "ຄວາມໄດ້ປຽບ_%"], ascending=False)

        save_files(final)

        st.success(f"ດຶງໄດ້ {len(final)} ຄູ່ ແລະບັນທຶກ file ແລ້ວ")

        show_cols = safe_columns(final, [
            "ລີກ", "ເວລາ", "ເຈົ້າບ້ານ", "ທີມຢາມ",
            "ລາຄາ_AH", "ຜົນ_live",
            "ຜົນວິເຄາະ", "ຄວາມໄດ້ປຽບ_%",
            "ຄວາມໝັ້ນໃຈ_%", "ຄຸນນະພາບຂໍ້ມູນ_%",
            "Home_%", "Draw_%", "Away_%", "OU", "OU_%", "AH",
            "Demand", "Supply", "Demand-Supply", "Logic_Power",
            "Sign_AH_Form", "Sign_Goal_H2H",
            "games", "avg_goal", "h2h", "ລະດັບຂໍ້ມູນ", "ເຫດຜົນ"
        ])

        st.subheader("📊 5 ຄູ່ທີ່ຂໍ້ມູນ + Logic ຊີ້ຄວາມໄດ້ປຽບສູງ")
        st.dataframe(final[show_cols].head(5), use_container_width=True)

        st.subheader("📈 ຜົນວິເຄາະທັງໝົດ")
        st.dataframe(final[show_cols], use_container_width=True)

        csv = final.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ ດາວໂຫຼດ CSV", csv, "v31_full_logic.csv", "text/csv", use_container_width=True)

with tab_file:
    latest = load_latest()
    hist = load_history()

    st.subheader("📂 ຂໍ້ມູນລ່າສຸດຈາກ CSV")
    if latest.empty:
        st.warning("ຍັງບໍ່ມີ file")
    else:
        st.dataframe(latest, use_container_width=True)

    st.subheader("🕘 ປະຫວັດ SQLite")
    st.dataframe(hist, use_container_width=True)
