import json, math, re
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="V17 PRO", page_icon="⚽", layout="wide")

API_URL = "https://goal7.co/data/update2_backup_json.php"
ANALYSE_URL = "https://goal7.co/analyse/?id={match_id}"
PRICEBALL_URL = "https://goal7.co/priceball/?i={match_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
    "Cache-Control": "no-cache",
}

def t(x: Any) -> str:
    return "" if x is None else str(x).strip()

def n(x: Any, default=0.0) -> float:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        return float(s) if s else default
    except:
        return default

def fetch(url: str, cookie: str = "") -> Dict[str, Any]:
    h = HEADERS.copy()
    if cookie.strip():
        h["Cookie"] = cookie.strip()
    try:
        r = requests.get(url, headers=h, timeout=25)
        return {"ok": r.status_code == 200, "status": r.status_code, "text": r.text, "headers": dict(r.headers), "error": ""}
    except Exception as e:
        return {"ok": False, "status": 0, "text": "", "headers": {}, "error": str(e)}

def parse_json_rows(raw: str) -> List[list]:
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except:
        return []

def rows_to_df(rows: List[list]) -> pd.DataFrame:
    cols = ["id","home_score","away_score","s1","s2","s3","s4","s5","time","home","away","league"]
    if not rows:
        return pd.DataFrame(columns=cols)
    max_len = max(len(r) for r in rows if isinstance(r, list))
    while len(cols) < max_len:
        cols.append(f"raw_{len(cols)}")
    fixed = [(r + [""] * max_len)[:max_len] for r in rows if isinstance(r, list)]
    return pd.DataFrame(fixed, columns=cols[:max_len]).astype(str)

def clean_team_name(x: str) -> str:
    x = unquote(t(x))
    x = re.sub(r"<.*?>", " ", x)
    x = re.sub(r"\s+", " ", x)
    x = x.replace("วิเคราะห์", "").replace("ราคาบอล", "")
    x = x.strip(" -|,[]()")
    return x[:80]

def split_vs(text: str) -> Tuple[str, str]:
    text = clean_team_name(text)
    patterns = [
        r"(.+?)\s+vs\s+(.+?)(?:\s|$)",
        r"(.+?)\s+VS\s+(.+?)(?:\s|$)",
        r"(.+?)\s+v\s+(.+?)(?:\s|$)",
        r"(.+?)\s+-\s+(.+?)(?:\s|$)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            home = clean_team_name(m.group(1))
            away = clean_team_name(m.group(2))
            if len(home) >= 2 and len(away) >= 2:
                return home, away
    return "", ""

def extract_names_from_html(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title")
    if title:
        home, away = split_vs(title.get_text(" ", strip=True))
        if home and away:
            return home, away

    meta_keys = ["og:title", "twitter:title", "description"]
    for key in meta_keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            home, away = split_vs(tag.get("content"))
            if home and away:
                return home, away

    html_text = unquote(html)

    js_patterns = [
        r'homeTeamName\s*[:=]\s*[\'"]([^\'"]+)[\'"].{0,120}?awayTeamName\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        r'home_name\s*[:=]\s*[\'"]([^\'"]+)[\'"].{0,120}?away_name\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
        r'team_home\s*[:=]\s*[\'"]([^\'"]+)[\'"].{0,120}?team_away\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
    ]
    for p in js_patterns:
        m = re.search(p, html_text, re.I | re.S)
        if m:
            return clean_team_name(m.group(1)), clean_team_name(m.group(2))

    body = soup.get_text(" ", strip=True)
    home, away = split_vs(body)
    return home, away

@st.cache_data(ttl=300, show_spinner=False)
def get_team_names(match_id: str, cookie: str) -> Dict[str, Any]:
    logs = []

    for label, url in [
        ("priceball", PRICEBALL_URL.format(match_id=match_id)),
        ("analyse", ANALYSE_URL.format(match_id=match_id)),
    ]:
        res = fetch(url, cookie)
        logs.append(f"{label}: {res['status']}")
        if res["ok"]:
            home, away = extract_names_from_html(res["text"])
            if home and away:
                return {"home": home, "away": away, "source": label, "logs": logs}

    return {"home": "", "away": "", "source": "", "logs": logs}

def poisson(lam: float, k: int) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def ai_calc(row) -> Dict[str, Any]:
    hs, aw = n(row.get("home_score")), n(row.get("away_score"))
    lh, la = max(0.45, hs + 0.95), max(0.45, aw + 0.75)

    hw = dr = awy = over = under = 0.0
    for h in range(7):
        for a in range(7):
            p = poisson(lh, h) * poisson(la, a)
            if h > a: hw += p
            elif h == a: dr += p
            else: awy += p
            if h + a >= 3: over += p
            else: under += p

    total = hw + dr + awy
    if total:
        hw, dr, awy = hw/total, dr/total, awy/total

    side, prob = max(
        [("ເຈົ້າບ້ານ", hw), ("ສະເໝີ", dr), ("ທີມຢາມ", awy)],
        key=lambda x: x[1]
    )

    ou = "ສູງ 2.5" if over >= under else "ຕ່ຳ 2.5"
    oup = max(over, under) / max(over + under, 0.0001)

    return {
        "AI_ຝັ່ງ": side,
        "AI_%": round(prob * 100, 2),
        "OU": ou,
        "OU_%": round(oup * 100, 2),
    }

def build_table(df: pd.DataFrame, cookie: str, limit: int) -> pd.DataFrame:
    out = []
    for i, (_, row) in enumerate(df.iterrows()):
        match_id = t(row.get("id"))
        names = {"home": t(row.get("home")), "away": t(row.get("away")), "source": "xhr"}

        if i < limit and match_id:
            got = get_team_names(match_id, cookie)
            if got["home"] and got["away"]:
                names = got

        ai = ai_calc(row)

        value = 45
        reasons = []
        if names["home"] and names["away"]:
            value += 20
            reasons.append("ດຶງຊື່ທີມໄດ້")
        if ai["AI_%"] >= 60:
            value += 20
            reasons.append("AI ຝັ່ງຫຼັກສູງ")
        if ai["OU_%"] >= 60:
            value += 10
            reasons.append("O/U ຊັດ")
        value = min(99, value)

        out.append({
            "ລະຫັດ": match_id,
            "ເວລາ": t(row.get("time")),
            "ເຈົ້າບ້ານ": names["home"],
            "ທີມຢາມ": names["away"],
            "ແຫຼ່ງຊື່": names["source"],
            "ສະກໍ": f"{t(row.get('home_score'))}-{t(row.get('away_score'))}",
            "AI_ຝັ່ງ": ai["AI_ຝັ່ງ"],
            "AI_%": ai["AI_%"],
            "OU": ai["OU"],
            "OU_%": ai["OU_%"],
            "Value_%": value,
            "ເຫດຜົນ": " | ".join(reasons),
        })

    result = pd.DataFrame(out)
    if not result.empty:
        result = result.sort_values(["Value_%", "AI_%"], ascending=False)
    return result

st.title("⚽ V17 PRO")
st.caption("ດຶງຊື່ທີມຈາກ priceball/analyse + XHR + AI")

cookie = st.text_area("ວາງ Cookie ທັງແຖວ", height=120)
limit = st.number_input("ຈຳນວນຄູ່ທີ່ຈະດຶງຊື່ທີມ", min_value=1, max_value=80, value=15)
show_raw = st.checkbox("ສະແດງຂໍ້ມູນດິບ", value=False)

if st.button("🚀 ດຶງຂໍ້ມູນ + ດຶງຊື່ທີມ", use_container_width=True):
    res = fetch(API_URL, cookie)

    c1, c2, c3 = st.columns(3)
    c1.metric("ສະຖານະ", res["status"])
    c2.metric("ປະເພດ", res["headers"].get("content-type", "-"))
    c3.metric("ຂະໜາດ", len(res["text"]))

    if not res["ok"]:
        st.error(res["error"] or res["text"][:500])
        st.stop()

    rows = parse_json_rows(res["text"])
    if not rows:
        st.error("ແປງ JSON ບໍ່ໄດ້")
        st.code(res["text"][:1000])
        st.stop()

    df = rows_to_df(rows)
    final = build_table(df, cookie, int(limit))

    st.success(f"ດຶງ XHR ໄດ້ {len(df)} ແຖວ")

    st.subheader("🔥 5 ຄູ່ເດັດ V17")
    st.dataframe(final.head(5), use_container_width=True)

    st.subheader("📊 ຕາຕະລາງທັງໝົດ")
    st.dataframe(final, use_container_width=True)

    st.subheader("📋 XHR ດິບ")
    st.dataframe(df, use_container_width=True)

    csv = final.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ ດາວໂຫຼດ CSV", csv, "v17_pro.csv", "text/csv", use_container_width=True)

    if show_raw:
        st.json(rows[:10])

st.info("ຕັ້ງຈຳນວນດຶງຊື່ທີມ 5-15 ກ່ອນ. ຖ້າດຶງບໍ່ໄດ້ ໃຫ້ຈັບ Cookie ໃໝ່.")
