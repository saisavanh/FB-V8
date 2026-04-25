import re, json, math, time, requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="V27 API GOD", page_icon="⚽", layout="wide")

BASE = "https://goal7.co"
API_XHR = "https://goal7.co/data/update2_backup_json.php"
PAGE_URL = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json,text/html,*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE_URL,
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6",
    "Cache-Control": "no-cache",
}

def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()

def request_url(url, cookie=""):
    h = HEADERS.copy()
    if cookie.strip():
        h["Cookie"] = cookie.strip()
    try:
        r = requests.get(url, headers=h, timeout=30)
        return r.status_code, r.text, dict(r.headers), r.url
    except Exception as e:
        return 0, str(e), {}, url

def parse_api_rows(text):
    try:
        data = json.loads(text)
        if not isinstance(data, list):
            return pd.DataFrame()
        rows = []
        for r in data:
            if not isinstance(r, list):
                continue
            rows.append({
                "match_id": str(r[0]) if len(r) > 0 else "",
                "home_score": str(r[1]) if len(r) > 1 else "",
                "away_score": str(r[2]) if len(r) > 2 else "",
                "time": str(r[8]) if len(r) > 8 else "",
                "raw_api": " | ".join(map(str, r)),
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

def is_team(x):
    return "[" in clean(x) and "]" in clean(x)

def is_price(x):
    x = clean(x)
    return any(k in x for k in ["0/0.5", "0.5", "1/1.5", "1.5", "เสมอ", "/", "-"])

def parse_page(html):
    soup = BeautifulSoup(html, "lxml")
    rows, league = [], ""

    for tr in soup.find_all("tr"):
        cols = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        txt = " | ".join(cols)

        if len(cols) < 5:
            if any(k in txt.lower() for k in ["league", "liga", "cup", "serie", "premier", "bundesliga"]):
                league = txt
            continue

        teams = [c for c in cols if is_team(c)]
        prices = [c for c in cols if is_price(c)]

        links = []
        for a in tr.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = BASE + href
            if "goal7.co" in href:
                links.append(href)

        mid = ""
        raw_links = " ".join(links)
        m = re.search(r"(?:id=|i=)(\d+)", raw_links)
        if m:
            mid = m.group(1)

        if len(teams) >= 2:
            rows.append({
                "match_id": mid,
                "ລີກ": league,
                "ເວລາ": cols[0] if cols else "",
                "ເຈົ້າບ້ານ": teams[0],
                "ລາຄາ_AH": prices[0] if prices else "",
                "ທີມຢາມ": teams[1],
                "ຜົນ_live": next((c for c in cols if re.search(r"\d+\s*-\s*\d+|\?\s*-\s*\?", c)), ""),
                "analyse_link": next((x for x in links if "analyse" in x), ""),
                "raw_page": txt,
            })
    return pd.DataFrame(rows)

def parse_ah(price):
    if "เสมอ" in clean(price):
        return 0.0
    m = re.findall(r"-?\d+(?:\.\d+)?", clean(price))
    return float(m[0]) if m else 0.0

def analyse_deep(url, cookie=""):
    if not url:
        return {"form": 0, "avg_goal": 0, "h2h": 0}
    status, html, _, _ = request_url(url, cookie)
    if status != 200:
        return {"form": 0, "avg_goal": 0, "h2h": 0}
    txt = BeautifulSoup(html, "lxml").get_text(" ", strip=True)

    scores = re.findall(r"(\d+)\s*-\s*(\d+)", txt)
    goals = [int(a) + int(b) for a, b in scores[:12]]
    avg_goal = sum(goals) / len(goals) if goals else 0

    w = len(re.findall(r"\bW\b|ชนะ|ຊະນະ", txt))
    l = len(re.findall(r"\bL\b|แพ้|ແພ້", txt))
    d = len(re.findall(r"\bD\b|เสมอ|ສະເໝີ", txt))

    return {"form": w - l, "avg_goal": avg_goal, "h2h": len(scores), "draw": d}

def ai(row, deep):
    ah = parse_ah(row.get("ລາຄາ_AH", ""))
    raw = clean(row.get("raw_page", "")) + " " + clean(row.get("raw_api", ""))

    home, away = 52.0, 48.0
    reason = ["ເຈົ້າບ້ານໄດ້ home advantage"]

    if ah < 0:
        home += abs(ah) * 18
        reason.append("AH ເຂົ້າທາງເຈົ້າບ້ານ")
    elif ah > 0:
        away += abs(ah) * 18
        reason.append("AH ເຂົ້າທາງທີມຢາມ")

    if "ต่อ" in raw:
        home += 7
        reason.append("ຂໍ້ຄວາມມີຝັ່ງຕໍ່")
    if "รอง" in raw:
        away += 7
        reason.append("ຂໍ້ຄວາມມີຝັ່ງຮອງ")

    if deep.get("form", 0) > 0:
        home += deep["form"] * 2.5
        reason.append("ຟອມ analyse ດີ")
    elif deep.get("form", 0) < 0:
        away += abs(deep["form"]) * 2.5
        reason.append("ຟອມ analyse ໄປທາງຢາມ")

    total = home + away
    hp, ap = home / total * 100, away / total * 100
    pick = "ເຈົ້າບ້ານ" if hp >= ap else "ທີມຢາມ"
    conf = max(hp, ap)

    ou = "ສູງ" if deep.get("avg_goal", 0) >= 2.5 else "ຕ່ຳ"
    oup = 62 if deep.get("avg_goal", 0) else 50

    value = conf + (8 if abs(ah) >= 0.5 else 0) + (6 if deep.get("h2h", 0) else 0)
    value = min(99, round(value, 2))

    alert = "🚨 STRONG" if value >= 85 else "⚠️ BET" if value >= 75 else "📊 WATCH" if value >= 65 else "—"

    return pd.Series({
        "AI_ຝັ່ງ": pick,
        "AI_%": round(conf, 2),
        "AH": ah,
        "OU": ou,
        "OU_%": oup,
        "Value_%": value,
        "Alert": alert,
        "ເຫດຜົນ": " | ".join(reason)
    })

st.title("⚽ V27 API GOD")
st.caption("XHR API + ຕາຕະລາງຈິງ + analyse ລຶກ + AI %")

cookie = st.text_area("Cookie ຖ້າຈຳເປັນ", height=80)
limit = st.number_input("ຈຳນວນຄູ່ທີ່ຈະເຂົ້າ analyse", 0, 80, 10)
debug = st.checkbox("Debug", value=False)

if st.button("🚀 RUN V27 API GOD", use_container_width=True):
    s1, api_text, _, _ = request_url(API_XHR, cookie)
    api_df = parse_api_rows(api_text)

    s2, html, _, final_url = request_url(PAGE_URL, cookie)
    page_df = parse_page(html)

    st.success(f"API: {s1} | PAGE: {s2} | API rows: {len(api_df)} | PAGE rows: {len(page_df)}")

    if page_df.empty:
        st.error("ບໍ່ພົບຕາຕະລາງຈາກ page")
        st.stop()

    df = page_df.copy()

    if not api_df.empty and "match_id" in df.columns:
        df = df.merge(api_df, on="match_id", how="left")

    final_rows = []
    for i, row in df.iterrows():
        deep = {"form": 0, "avg_goal": 0, "h2h": 0}
        if i < int(limit):
            deep = analyse_deep(row.get("analyse_link", ""), cookie)
            time.sleep(0.4)

        out = row.to_dict()
        out.update(deep)
        out.update(ai(pd.Series(out), deep).to_dict())
        final_rows.append(out)

    final = pd.DataFrame(final_rows).sort_values(["Value_%", "AI_%"], ascending=False)

    st.subheader("🔥 TOP 5 V27")
    st.dataframe(final.head(5), use_container_width=True)

    st.subheader("🚨 SIGNAL")
    st.dataframe(final[final["Alert"] != "—"], use_container_width=True)

    st.subheader("📊 ທັງໝົດ")
    st.dataframe(final, use_container_width=True)

    csv = final.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ CSV", csv, "v27_api_god.csv", "text/csv", use_container_width=True)

    if debug:
        st.code(api_text[:1200])
        st.code(html[:1200])
