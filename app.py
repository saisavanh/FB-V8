import json
import math
import re
from typing import Any, List, Dict

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="V14 AI เซียน",
    page_icon="⚽",
    layout="wide"
)

API_URL = "https://goal7.co/data/update2_backup_json.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
}


def txt(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def num(x: Any, default: float = 0.0) -> float:
    try:
        s = str(x).replace(",", "").replace("%", "").strip()
        if s == "":
            return default
        return float(s)
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
        return {
            "ok": False,
            "status": 0,
            "text": "",
            "headers": {},
            "error": str(e),
        }


def parse_json(text: str) -> List[list]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except Exception:
        pass
    return []


def make_columns(max_len: int) -> List[str]:
    cols = [
        "id",
        "home_score",
        "away_score",
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "time",
        "home",
        "away",
        "league",
    ]
    while len(cols) < max_len:
        cols.append(f"raw_{len(cols)}")
    return cols[:max_len]


def rows_to_df(rows: List[list]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    max_len = max(len(r) for r in rows if isinstance(r, list))
    cols = make_columns(max_len)

    fixed = []
    for r in rows:
        if not isinstance(r, list):
            continue
        rr = r + [""] * (max_len - len(r))
        fixed.append(rr[:max_len])

    return pd.DataFrame(fixed, columns=cols)


def find_odds(row: pd.Series) -> List[float]:
    raw = " ".join([txt(v) for v in row.values])
    vals = []
    for x in re.findall(r"\b\d+\.\d+\b", raw):
        v = num(x)
        if 1.01 <= v <= 20:
            vals.append(v)
    return vals


def poisson_ai(row: pd.Series) -> Dict[str, Any]:
    hs = num(row.get("home_score", 0))
    away_s = num(row.get("away_score", 0))

    lam_home = max(0.45, hs + 0.95)
    lam_away = max(0.45, away_s + 0.75)

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over25 = 0.0
    under25 = 0.0

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
    if total > 0:
        home_win /= total
        draw /= total
        away_win /= total

    ou_total = over25 + under25
    if ou_total > 0:
        over25 /= ou_total
        under25 /= ou_total

    if home_win >= away_win and home_win >= draw:
        side = "ເຈົ້າບ້ານ"
        prob = home_win
    elif away_win >= home_win and away_win >= draw:
        side = "ທີມຢາມ"
        prob = away_win
    else:
        side = "ສະເໝີ"
        prob = draw

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
    odds = find_odds(row)

    value_score = 0
    reason = []

    if ai["AI_ຝັ່ງ_%"] >= 62:
        value_score += 25
        reason.append("ຄວາມນ່າຈະເປັນຝັ່ງຫຼັກສູງ")

    if ai["OU_%"] >= 60:
        value_score += 20
        reason.append("O/U ມີທິດທາງຊັດ")

    if odds:
        avg_odd = sum(odds[:8]) / min(len(odds), 8)
        if avg_odd >= 2.00:
            value_score += 25
            reason.append("ພົບລາຄາທີ່ອາດມີ Value")
        elif avg_odd >= 1.70:
            value_score += 15
            reason.append("ລາຄາຢູ່ໂຊນຫຼິ້ນໄດ້")
        else:
            value_score += 5
            reason.append("ລາຄາຕ່ຳ ຕ້ອງລະວັງ")
    else:
        reason.append("ຍັງບໍ່ພົບລາຄາໃນ row")

    hs = num(row.get("home_score", 0))
    aw = num(row.get("away_score", 0))
    if abs(hs - aw) >= 1:
        value_score += 10
        reason.append("ຄະແນນມີຝັ່ງໄດ້ປຽບ")

    value_score = min(99, max(1, value_score + 35))

    if value_score >= 82:
        level = "🔥 ຄູ່ເດັດເຊັຽນ"
    elif value_score >= 70:
        level = "✅ ນ່າຫຼິ້ນ"
    elif value_score >= 58:
        level = "🟡 ພໍເບິ່ງໄດ້"
    else:
        level = "⚠️ ລໍຖ້າ"

    return {
        "Value_%": value_score,
        "ລະດັບ": level,
        "ເຫດຜົນ": " | ".join(reason),
    }


def build_ai_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        ai = poisson_ai(row)
        val = value_ai(row, ai)

        rows.append({
            "ລີກ": txt(row.get("league", "")),
            "ລະຫັດ": txt(row.get("id", "")),
            "ເວລາ": txt(row.get("time", "")),
            "ເຈົ້າບ້ານ": txt(row.get("home", "")),
            "ທີມຢາມ": txt(row.get("away", "")),
            "ສະກໍ": f"{txt(row.get('home_score',''))}-{txt(row.get('away_score',''))}",
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


st.title("⚽ V14 AI ລະດັບເຊັຽນ")
st.caption("Poisson + Probability + O/U + Value Bet + Top 5 ຄູ່ເດັດ")

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
    ai_df = build_ai_table(df)

    st.success(f"ດຶງຂໍ້ມູນໄດ້ {len(df)} ແຖວ")

    st.subheader("🔥 5 ຄູ່ເດັດ AI ເຊັຽນ")
    st.dataframe(ai_df.head(5), use_container_width=True)

    st.subheader("📊 ຜົນວິເຄາະທັງໝົດ")
    st.dataframe(ai_df, use_container_width=True)

    st.subheader("📋 ຂໍ້ມູນດຶງຈາກ XHR")
    st.dataframe(df, use_container_width=True)

    csv = ai_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ ດາວໂຫຼດຜົນວິເຄາະ CSV",
        csv,
        "v14_ai_analysis.csv",
        "text/csv",
        use_container_width=True
    )

    if show_raw:
        st.subheader("ຂໍ້ມູນດິບ")
        st.json(rows[:10])

st.info("ຖ້າ Status ບໍ່ແມ່ນ 200 ຫຼືດຶງບໍ່ໄດ້: Cookie ໝົດອາຍຸ ໃຫ້ຈັບ Cookie ໃໝ່ຈາກ HTTP Sniffer.")
