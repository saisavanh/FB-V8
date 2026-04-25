import json
import math
import re
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="V14 FULL AI", page_icon="⚽", layout="wide")

API_URL = "https://goal7.co/data/update2_backup_json.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
}


def text(x: Any) -> str:
    return "" if x is None else str(x).strip()


def num(x: Any, default: float = 0.0) -> float:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        return float(s) if s else default
    except Exception:
        return default


def poisson(lam: float, k: int) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)


def fetch_data(cookie: str) -> Dict[str, Any]:
    headers = HEADERS.copy()
    if cookie.strip():
        headers["Cookie"] = cookie.strip()

    try:
        r = requests.get(API_URL, headers=headers, timeout=25)
        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "text": r.text,
            "headers": dict(r.headers),
            "error": "",
        }
    except Exception as e:
        return {"ok": False, "status": 0, "text": "", "headers": {}, "error": str(e)}


def parse_json(raw: str) -> List[list]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except Exception:
        return []
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


def find_odds(row: pd.Series) -> List[float]:
    raw = " ".join(text(v) for v in row.values)
    vals = []
    for x in re.findall(r"\b\d+\.\d+\b", raw):
        v = num(x)
        if 1.01 <= v <= 20:
            vals.append(v)
    return vals


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
        home_win, draw, away_win = home_win / total, draw / total, away_win / total

    ou_total = over25 + under25
    if ou_total:
        over25, under25 = over25 / ou_total, under25 / ou_total

    if home_win >= draw and home_win >= away_win:
        side, prob = "ເຈົ້າບ້ານ", home_win
    elif away_win >= draw and away_win >= home_win:
        side, prob = "ທີມຢາມ", away_win
    else:
        side, prob = "ສະເໝີ", draw

    ou_pick = "ສູງ 2.5" if over25 >= under25 else "ຕ່ຳ 2.5"
    ou_prob = max(over25, under25)

    return {
        "AI_ຝັ່ງ": side,
        "AI_ຝັ່ງ_%": round(prob * 100, 2),
        "ເຈົ້າບ້ານ_%": round(home_win * 100, 2),
        "ສະເໝີ_%": round(draw * 100, 2),
        "ທີມຢາມ_%": round(away_win * 100, 2),
        "OU_AI": ou_pick,
        "OU_%": round(ou_prob * 100, 2),
    }


def value_ai(row: pd.Series, ai: Dict[str, Any]) -> Dict[str, Any]:
    score = 35
    reasons = []
    odds = find_odds(row)

    if ai["AI_ຝັ່ງ_%"] >= 62:
        score += 25
        reasons.append("ຄວາມນ່າຈະເປັນຝັ່ງຫຼັກສູງ")
    if ai["OU_%"] >= 60:
        score += 18
        reasons.append("O/U ຊັດເຈນ")

    if odds:
        avg_odd = sum(odds[:8]) / min(len(odds), 8)
        if avg_odd >= 2.00:
            score += 22
            reasons.append("ລາຄາມີໂອກາດ Value")
        elif avg_odd >= 1.70:
            score += 12
            reasons.append("ລາຄາຢູ່ໂຊນຫຼິ້ນໄດ້")
        else:
            score += 5
            reasons.append("ລາຄາຕ່ຳ ຕ້ອງລະວັງ")
    else:
        reasons.append("ຍັງບໍ່ພົບລາຄາໃນ row")

    hs = num(row.get("home_score", 0))
    aw = num(row.get("away_score", 0))
    if abs(hs - aw) >= 1:
        score += 8
        reasons.append("ສະກໍມີຝັ່ງໄດ້ປຽບ")

    score = max(1, min(99, score))

    if score >= 82:
        level = "🔥 ຄູ່ເດັດ"
    elif score >= 70:
        level = "✅ ນ່າຫຼິ້ນ"
    elif score >= 58:
        level = "🟡 ພໍເບິ່ງ"
    else:
        level = "⚠️ ລໍຖ້າ"

    return {"Value_%": score, "ລະດັບ": level, "ເຫດຜົນ": " | ".join(reasons)}


def build_ai(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        ai = poisson_ai(row)
        val = value_ai(row, ai)

        rows.append({
            "ລີກ": text(row.get("league", "")),
            "ລະຫັດ": text(row.get("id", "")),
            "ເວລາ": text(row.get("time", "")),
            "ເຈົ້າບ້ານ": text(row.get("home", "")),
            "ທີມຢາມ": text(row.get("away", "")),
            "ສະກໍ": f"{text(row.get('home_score',''))}-{text(row.get('away_score',''))}",
            "AI_ຝັ່ງ": ai["AI_ຝັ່ງ"],
            "AI_ຝັ່ງ_%": ai["AI_ຝັ່ງ_%"],
            "OU_AI": ai["OU_AI"],
            "OU_%": ai["OU_%"],
            "ເຈົ້າບ້ານ_%": ai["ເຈົ້າບ້ານ_%"],
            "ສະເໝີ_%": ai["ສະເໝີ_%"],
            "ທີມຢາມ_%": ai["ທີມຢາມ_%"],
            "Value_%": val["Value_%"],
            "ລະດັບ": val["ລະດັບ"],
            "ເຫດຜົນ": val["ເຫດຜົນ"],
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["Value_%", "AI_ຝັ່ງ_%"], ascending=False)
    return out


st.title("⚽ V14 FULL AI ລະດັບເຊັຽນ")
st.caption("XHR JSON + Cookie + Poisson + Probability + O/U + Value Bet + Top 5")

cookie = st.text_area(
    "ວາງ Cookie ທັງແຖວ",
    height=120,
    placeholder="_ga=...; cf_clearance=...; PHPSESSID=..."
)

show_raw = st.checkbox("ສະແດງຂໍ້ມູນດິບ", value=False)

if st.button("🚀 ດຶງຂໍ້ມູນ + AI ເຊັຽນ", use_container_width=True):
    res = fetch_data(cookie)

    c1, c2, c3 = st.columns(3)
    c1.metric("ສະຖານະ", res["status"])
    c2.metric("ປະເພດ", res["headers"].get("content-type", "-"))
    c3.metric("ຂະໜາດ", len(res["text"]))

    if not res["ok"]:
        st.error(res["error"] or res["text"][:500])
        st.stop()

    rows = parse_json(res["text"])
    if not rows:
        st.warning("ດຶງໄດ້ ແຕ່ແປງ JSON ບໍ່ໄດ້")
        st.code(res["text"][:1000])
        st.stop()

    df = rows_to_df(rows)
    ai_df = build_ai(df)

    st.success(f"ດຶງຂໍ້ມູນໄດ້ {len(df)} ແຖວ")

    st.subheader("🔥 5 ຄູ່ເດັດ AI")
    st.dataframe(ai_df.head(5), use_container_width=True)

    st.subheader("📊 ຜົນວິເຄາະທັງໝົດ")
    st.dataframe(ai_df, use_container_width=True)

    st.subheader("📋 ຂໍ້ມູນ XHR")
    st.dataframe(df, use_container_width=True)

    csv = ai_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ ດາວໂຫຼດ CSV",
        csv,
        "v14_full_ai.csv",
        "text/csv",
        use_container_width=True
    )

    if show_raw:
        st.subheader("ຂໍ້ມູນດິບ")
        st.json(rows[:10])

st.info("ຖ້າ Status ບໍ່ແມ່ນ 200 ຫຼືດຶງບໍ່ໄດ້: Cookie ໝົດອາຍຸ ໃຫ້ຈັບ Cookie ໃໝ່ຈາກ HTTP Sniffer.")
