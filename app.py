import json
import math
import re
from typing import Any, Dict, List, Tuple

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="V16 FULL", page_icon="⚽", layout="wide")

API_URL = "https://goal7.co/data/update2_backup_json.php"
ANALYSE_URL = "https://goal7.co/analyse/?id={match_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
    "Cache-Control": "no-cache",
}


def text(x: Any) -> str:
    return "" if x is None else str(x).strip()


def num(x: Any, default: float = 0.0) -> float:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        return float(s) if s else default
    except Exception:
        return default


def fetch(url: str, cookie: str = "", is_json: bool = False) -> Dict[str, Any]:
    headers = HEADERS.copy()
    if cookie.strip():
        headers["Cookie"] = cookie.strip()

    try:
        r = requests.get(url, headers=headers, timeout=25)
        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "text": r.text,
            "headers": dict(r.headers),
            "json": r.json() if is_json and r.status_code == 200 else None,
            "error": "",
        }
    except Exception as e:
        return {
            "ok": False,
            "status": 0,
            "text": "",
            "headers": {},
            "json": None,
            "error": str(e),
        }


def parse_json_rows(raw: str) -> List[list]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except Exception:
        pass
    return []


def make_columns(n: int) -> List[str]:
    cols = [
        "id", "home_score", "away_score", "s1", "s2", "s3", "s4", "s5",
        "time", "home", "away", "league"
    ]
    while len(cols) < n:
        cols.append(f"raw_{len(cols)}")
    return cols[:n]


def rows_to_df(rows: List[list]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    max_len = max(len(r) for r in rows if isinstance(r, list))
    cols = make_columns(max_len)

    fixed = []
    for r in rows:
        if isinstance(r, list):
            fixed.append((r + [""] * max_len)[:max_len])

    df = pd.DataFrame(fixed, columns=cols)
    for c in df.columns:
        df[c] = df[c].astype(str)
    return df


def extract_team_names_from_title(title: str) -> Tuple[str, str]:
    t = text(title)
    t = re.sub(r"\s+", " ", t)

    patterns = [
        r"(.+?)\s+vs\s+(.+?)(?:\s|$)",
        r"(.+?)\s+VS\s+(.+?)(?:\s|$)",
        r"(.+?)\s+v\s+(.+?)(?:\s|$)",
        r"(.+?)\s+-\s+(.+?)(?:\s|$)",
    ]

    for p in patterns:
        m = re.search(p, t, re.I)
        if m:
            home = m.group(1).strip(" -|,")
            away = m.group(2).strip(" -|,")
            if len(home) >= 2 and len(away) >= 2:
                return home[:80], away[:80]

    return "", ""


def extract_team_names(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title")
    if title:
        home, away = extract_team_names_from_title(title.get_text(" ", strip=True))
        if home and away:
            return home, away

    body = soup.get_text(" ", strip=True)
    body = re.sub(r"\s+", " ", body)

    home, away = extract_team_names_from_title(body)
    if home and away:
        return home, away

    return "", ""


def extract_odds_from_html(html: str) -> Dict[str, Any]:
    nums = []
    for x in re.findall(r"\b\d+\.\d+\b", html):
        v = num(x)
        if 1.01 <= v <= 20:
            nums.append(v)

    return {
        "odds_count": len(nums),
        "odds_sample": nums[:12],
        "avg_odds": round(sum(nums[:12]) / min(len(nums), 12), 3) if nums else 0,
    }


@st.cache_data(ttl=300, show_spinner=False)
def analyse_cached(match_id: str, cookie: str) -> Dict[str, Any]:
    url = ANALYSE_URL.format(match_id=match_id)
    res = fetch(url, cookie=cookie)

    if not res["ok"]:
        return {
            "analyse_ok": False,
            "home": "",
            "away": "",
            "tables": 0,
            "analyse_text": "",
            "odds_count": 0,
            "avg_odds": 0,
        }

    home, away = extract_team_names(res["text"])
    odds = extract_odds_from_html(res["text"])

    try:
        tables = pd.read_html(res["text"])
        tables_count = len(tables)
    except Exception:
        tables_count = 0

    soup = BeautifulSoup(res["text"], "html.parser")
    analyse_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:1200]

    return {
        "analyse_ok": True,
        "home": home,
        "away": away,
        "tables": tables_count,
        "analyse_text": analyse_text,
        "odds_count": odds["odds_count"],
        "avg_odds": odds["avg_odds"],
    }


def poisson(lam: float, k: int) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def poisson_ai(row: pd.Series) -> Dict[str, Any]:
    hs = num(row.get("home_score", 0))
    aw = num(row.get("away_score", 0))

    lam_home = max(0.45, hs + 0.95)
    lam_away = max(0.45, aw + 0.75)

    home_win = draw = away_win = over25 = under25 = 0.0

    for h in range(7):
        for a in range(7):
            p = poisson(lam_home, h) * poisson(lam_away, a)

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if h + a >= 3:
                over25 += p
            else:
                under25 += p

    total = home_win + draw + away_win
    if total:
        home_win /= total
        draw /= total
        away_win /= total

    ou_total = over25 + under25
    if ou_total:
        over25 /= ou_total
        under25 /= ou_total

    if home_win >= draw and home_win >= away_win:
        side, prob = "ເຈົ້າບ້ານ", home_win
    elif away_win >= draw and away_win >= home_win:
        side, prob = "ທີມຢາມ", away_win
    else:
        side, prob = "ສະເໝີ", draw

    return {
        "AI_ຝັ່ງ": side,
        "AI_ຝັ່ງ_%": round(prob * 100, 2),
        "ເຈົ້າບ້ານ_%": round(home_win * 100, 2),
        "ສະເໝີ_%": round(draw * 100, 2),
        "ທີມຢາມ_%": round(away_win * 100, 2),
        "OU_AI": "ສູງ 2.5" if over25 >= under25 else "ຕ່ຳ 2.5",
        "OU_%": round(max(over25, under25) * 100, 2),
    }


def value_ai(row: pd.Series, ai: Dict[str, Any], analyse: Dict[str, Any]) -> Dict[str, Any]:
    score = 35
    reasons = []

    if ai["AI_ຝັ່ງ_%"] >= 62:
        score += 24
        reasons.append("AI ຝັ່ງຫຼັກສູງ")
    if ai["OU_%"] >= 60:
        score += 16
        reasons.append("O/U ມີທິດທາງ")

    if analyse.get("home") and analyse.get("away"):
        score += 14
        reasons.append("ດຶງຊື່ທີມໄດ້")
    else:
        reasons.append("ຊື່ທີມຍັງບໍ່ຄົບ")

    if analyse.get("tables", 0) > 0:
        score += 10
        reasons.append("ມີຕາຕະລາງສະຖິຕິ")

    avg_odds = num(analyse.get("avg_odds", 0))
    if avg_odds >= 2.0:
        score += 15
        reasons.append("ລາຄາມີໂອກາດ Value")
    elif avg_odds >= 1.7:
        score += 8
        reasons.append("ລາຄາຢູ່ໂຊນຫຼິ້ນໄດ້")

    score = max(1, min(99, score))

    if score >= 82:
        level = "🔥 ຄູ່ເດັດ"
    elif score >= 70:
        level = "✅ ນ່າຫຼິ້ນ"
    elif score >= 58:
        level = "🟡 ພໍເບິ່ງ"
    else:
        level = "⚠️ ລໍຖ້າ"

    return {
        "Value_%": score,
        "ລະດັບ": level,
        "ເຫດຜົນ": " | ".join(reasons),
    }


def build_ai(df: pd.DataFrame, cookie: str, limit_analyse: int) -> pd.DataFrame:
    out = []

    for i, (_, row) in enumerate(df.iterrows()):
        match_id = text(row.get("id", ""))

        analyse = {
            "analyse_ok": False,
            "home": text(row.get("home", "")),
            "away": text(row.get("away", "")),
            "tables": 0,
            "odds_count": 0,
            "avg_odds": 0,
            "analyse_text": "",
        }

        if match_id and i < limit_analyse:
            analyse2 = analyse_cached(match_id, cookie)
            analyse.update(analyse2)

        ai = poisson_ai(row)
        val = value_ai(row, ai, analyse)

        home = analyse.get("home") or text(row.get("home", ""))
        away = analyse.get("away") or text(row.get("away", ""))

        out.append({
            "ລະຫັດ": match_id,
            "ເວລາ": text(row.get("time", "")),
            "ລີກ": text(row.get("league", "")),
            "ເຈົ້າບ້ານ": home,
            "ທີມຢາມ": away,
            "ສະກໍ": f"{text(row.get('home_score',''))}-{text(row.get('away_score',''))}",
            "AI_ຝັ່ງ": ai["AI_ຝັ່ງ"],
            "AI_ຝັ່ງ_%": ai["AI_ຝັ່ງ_%"],
            "OU_AI": ai["OU_AI"],
            "OU_%": ai["OU_%"],
            "Value_%": val["Value_%"],
            "ລະດັບ": val["ລະດັບ"],
            "analyse_ok": analyse.get("analyse_ok"),
            "tables": analyse.get("tables"),
            "odds_count": analyse.get("odds_count"),
            "avg_odds": analyse.get("avg_odds"),
            "ເຫດຜົນ": val["ເຫດຜົນ"],
        })

    result = pd.DataFrame(out)
    if not result.empty:
        result = result.sort_values(["Value_%", "AI_ຝັ່ງ_%"], ascending=False)
    return result


st.title("⚽ V16 FULL")
st.caption("ແກ້ຊື່ທີມ: XHR JSON + scrape analyse + AI Poisson + Value Bet")

cookie = st.text_area(
    "ວາງ Cookie ທັງແຖວ",
    height=120,
    placeholder="_ga=...; cf_clearance=...; PHPSESSID=..."
)

limit_analyse = st.number_input(
    "ຈຳນວນ analyse ທີ່ຈະດຶງ",
    min_value=1,
    max_value=60,
    value=12
)

show_raw = st.checkbox("ສະແດງຂໍ້ມູນດິບ", value=False)

if st.button("🚀 ດຶງຂໍ້ມູນ + V16 AI", use_container_width=True):
    res = fetch(API_URL, cookie=cookie)

    m1, m2, m3 = st.columns(3)
    m1.metric("ສະຖານະ", res["status"])
    m2.metric("ປະເພດ", res["headers"].get("content-type", "-"))
    m3.metric("ຂະໜາດ", len(res["text"]))

    if not res["ok"]:
        st.error(res["error"] or res["text"][:500])
        st.stop()

    rows = parse_json_rows(res["text"])
    if not rows:
        st.warning("ດຶງໄດ້ ແຕ່ແປງ JSON ບໍ່ໄດ້")
        st.code(res["text"][:1000])
        st.stop()

    df = rows_to_df(rows)
    ai_df = build_ai(df, cookie, int(limit_analyse))

    st.success(f"ດຶງຂໍ້ມູນໄດ້ {len(df)} ແຖວ")

    st.subheader("🔥 5 ຄູ່ເດັດ V16")
    st.dataframe(ai_df.head(5), use_container_width=True)

    st.subheader("📊 ຜົນວິເຄາະທັງໝົດ")
    st.dataframe(ai_df, use_container_width=True)

    st.subheader("📋 ຂໍ້ມູນ XHR")
    st.dataframe(df, use_container_width=True)

    csv = ai_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ ດາວໂຫຼດ CSV",
        csv,
        "v16_full_ai.csv",
        "text/csv",
        use_container_width=True
    )

    if show_raw:
        st.subheader("ຂໍ້ມູນດິບ")
        st.json(rows[:10])

st.info("ຖ້າຊື່ທີມຍັງບໍ່ອອກ: ໜ້າ analyse ອາດມີໂຄງສ້າງຊື່ທີມຢູ່ໃນ JavaScript. ຕ້ອງຈັບ XHR ເພີ່ມທີ່ມີ team_name ໂດຍກົງ.")
