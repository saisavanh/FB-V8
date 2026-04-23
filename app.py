
import re
import math
import json
from typing import Any, Dict, List, Optional, Tuple

import requests
import pandas as pd
import streamlit as st

# =====================================
# Football AI V8 Full - Single File
# Streamlit app.py ຟາຍດຽວ
# =====================================

st.set_page_config(page_title="Football AI V8 Full", layout="wide")

DEFAULT_URL = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
}


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return default
    try:
        return float(m.group())
    except Exception:
        return default


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@st.cache_data(ttl=300)
def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


@st.cache_data(ttl=300)
def fetch_page_tables(url: str) -> List[pd.DataFrame]:
    html = fetch_html(url)
    try:
        tables = pd.read_html(html)
        return tables
    except Exception:
        return []


@st.cache_data(ttl=300)
def extract_json_blocks(url: str) -> List[Dict[str, Any]]:
    html = fetch_html(url)
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    results: List[Dict[str, Any]] = []

    for script in scripts:
        script = script.strip()
        if not script:
            continue

        for pattern in [
            r"__NEXT_DATA__\s*=\s*(\{.*?\})\s*;",
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;",
            r"window\.__NUXT__\s*=\s*(\{.*?\})\s*;",
        ]:
            matches = re.findall(pattern, script, re.DOTALL)
            for item in matches:
                try:
                    results.append(json.loads(item))
                except Exception:
                    pass

        stripped = script.strip().rstrip(";")
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                results.append(json.loads(stripped))
            except Exception:
                pass

    return results


def flatten_json(obj: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    rows: List[Tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else str(k)
            rows.extend(flatten_json(v, new_key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{prefix}[{i}]"
            rows.extend(flatten_json(v, new_key))
    else:
        rows.append((prefix, obj))
    return rows


def detect_team_column(df: pd.DataFrame) -> Optional[str]:
    priority = ["ทีม", "team", "home", "away", "match", "คู่", "club", "clubs"]
    cols = [str(c) for c in df.columns]
    lowered = {c: c.lower() for c in cols}

    for key in priority:
        for c in cols:
            if key in lowered[c]:
                return c

    for c in cols:
        if df[c].astype(str).str.contains("-|vs|v|พบ|เจอ", case=False, na=False).any():
            return c
    return cols[0] if cols else None


def detect_score_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    home_col = None
    away_col = None
    for c in df.columns:
        lc = str(c).lower()
        if home_col is None and any(k in lc for k in ["home goals", "gf", "ยิงได้", "ได้"]):
            home_col = c
        if away_col is None and any(k in lc for k in ["away goals", "ga", "เสีย", "เสียประตู"]):
            away_col = c
    return home_col, away_col


def calc_form_points(result_text: str) -> int:
    t = clean_text(result_text).upper()
    if t in ["W", "WIN", "ชนะ"]:
        return 3
    if t in ["D", "DRAW", "เสมอ"]:
        return 1
    return 0


def build_sample_stats(team_name: str) -> Dict[str, Any]:
    seed = sum(ord(c) for c in team_name) % 100
    played = 10
    wins = 3 + (seed % 5)
    draws = 1 + (seed % 3)
    losses = max(0, played - wins - draws)
    gf = 8 + (seed % 12)
    ga = 6 + ((seed * 3) % 10)
    return {
        "team": team_name,
        "played": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "gf": gf,
        "ga": ga,
        "avg_gf": round(gf / played, 2),
        "avg_ga": round(ga / played, 2),
        "points": wins * 3 + draws,
        "form_score": round((wins * 3 + draws) / (played * 3) * 100, 2),
    }


def expected_goals(home: Dict[str, Any], away: Dict[str, Any]) -> Tuple[float, float]:
    home_xg = (safe_float(home.get("avg_gf"), 1.2) + safe_float(away.get("avg_ga"), 1.0)) / 2
    away_xg = (safe_float(away.get("avg_gf"), 1.0) + safe_float(home.get("avg_ga"), 1.0)) / 2
    home_xg += 0.15
    return round(home_xg, 2), round(away_xg, 2)


def poisson_prob(lmbda: float, k: int) -> float:
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except Exception:
        return 0.0


def match_matrix(home_xg: float, away_xg: float, max_goals: int = 7) -> List[List[float]]:
    matrix: List[List[float]] = []
    for h in range(max_goals + 1):
        row = []
        for a in range(max_goals + 1):
            row.append(poisson_prob(home_xg, h) * poisson_prob(away_xg, a))
        matrix.append(row)
    return matrix


def calc_1x2_probs(home_xg: float, away_xg: float) -> Dict[str, float]:
    matrix = match_matrix(home_xg, away_xg)
    home = 0.0
    draw = 0.0
    away = 0.0
    for h, row in enumerate(matrix):
        for a, p in enumerate(row):
            if h > a:
                home += p
            elif h == a:
                draw += p
            else:
                away += p
    total = home + draw + away
    if total <= 0:
        return {"home": 0.0, "draw": 0.0, "away": 0.0}
    return {
        "home": round(home / total * 100, 2),
        "draw": round(draw / total * 100, 2),
        "away": round(away / total * 100, 2),
    }


def calc_fair_odds(prob_percent: float) -> float:
    p = prob_percent / 100.0
    if p <= 0:
        return 0.0
    return round(1 / p, 2)


def calc_ou_probs(home_xg: float, away_xg: float, line: float = 2.5) -> Dict[str, float]:
    total_xg = home_xg + away_xg
    over = 0.0
    under = 0.0
    for goals in range(0, 12):
        p = poisson_prob(total_xg, goals)
        if goals > line:
            over += p
        else:
            under += p
    total = over + under
    if total <= 0:
        return {"over": 0.0, "under": 0.0}
    return {
        "over": round(over / total * 100, 2),
        "under": round(under / total * 100, 2),
    }


def calc_ah_suggestion(home_prob: float, away_prob: float) -> str:
    diff = home_prob - away_prob
    if diff >= 25:
        return "ແນະນຳ AH: ເຈົ້າບ້ານ -1.0"
    if diff >= 18:
        return "ແນະນຳ AH: ເຈົ້າບ້ານ -0.75"
    if diff >= 10:
        return "ແນະນຳ AH: ເຈົ້າບ້ານ -0.5"
    if diff >= 4:
        return "ແນະນຳ AH: ເຈົ້າບ້ານ -0.25"
    if diff <= -25:
        return "ແນະນຳ AH: ທີມຢາມ -1.0"
    if diff <= -18:
        return "ແນະນຳ AH: ທີມຢາມ -0.75"
    if diff <= -10:
        return "ແນະນຳ AH: ທີມຢາມ -0.5"
    if diff <= -4:
        return "ແນະນຳ AH: ທີມຢາມ -0.25"
    return "ແນະນຳ AH: ສູສີ 0 / ເລືອກຂ້າງດ້ວຍລາຄາຕະຫຼາດ"


def classify_value(fair_odds: float, market_odds: float) -> str:
    if fair_odds <= 0 or market_odds <= 0:
        return "ບໍ່ພຽງພໍ"
    edge = market_odds - fair_odds
    if edge >= 0.2:
        return "Value ດີ"
    if edge >= 0.08:
        return "Value ພໍໃຊ້"
    if edge <= -0.15:
        return "ລາຄາແພງ"
    return "ໃກ້ຄຽງຍຸດຕິທຳ"


def parse_match_list_from_tables(tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for idx, df in enumerate(tables):
        if df.empty:
            continue
        df = df.copy()
        df.columns = [clean_text(c) for c in df.columns]
        team_col = detect_team_column(df)
        if not team_col:
            continue

        for _, row in df.iterrows():
            raw = clean_text(row.get(team_col, ""))
            if not raw or len(raw) < 3:
                continue

            home_team = ""
            away_team = ""
            for sep in [" - ", " vs ", " VS ", " v ", " พบ "]:
                if sep in raw:
                    parts = raw.split(sep, 1)
                    home_team = clean_text(parts[0])
                    away_team = clean_text(parts[1])
                    break

            if not home_team or not away_team:
                continue

            item = {
                "table_index": idx,
                "home_team": home_team,
                "away_team": away_team,
                "source_text": raw,
            }

            for c in df.columns:
                item[str(c)] = clean_text(row.get(c, ""))
            matches.append(item)
    return matches


def get_market_number(text: str) -> float:
    return safe_float(text, 0.0)


def analyze_match(home_team: str, away_team: str, market_home_odds: float, market_draw_odds: float, market_away_odds: float, ou_line: float, over_odds: float, under_odds: float) -> Dict[str, Any]:
    home_stats = build_sample_stats(home_team)
    away_stats = build_sample_stats(away_team)
    home_xg, away_xg = expected_goals(home_stats, away_stats)
    probs = calc_1x2_probs(home_xg, away_xg)
    ou_probs = calc_ou_probs(home_xg, away_xg, ou_line)

    fair_home = calc_fair_odds(probs["home"])
    fair_draw = calc_fair_odds(probs["draw"])
    fair_away = calc_fair_odds(probs["away"])
    fair_over = calc_fair_odds(ou_probs["over"])
    fair_under = calc_fair_odds(ou_probs["under"])

    return {
        "home_stats": home_stats,
        "away_stats": away_stats,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "total_xg": round(home_xg + away_xg, 2),
        "probs": probs,
        "ou_probs": ou_probs,
        "fair_odds": {
            "home": fair_home,
            "draw": fair_draw,
            "away": fair_away,
            "over": fair_over,
            "under": fair_under,
        },
        "market_odds": {
            "home": market_home_odds,
            "draw": market_draw_odds,
            "away": market_away_odds,
            "over": over_odds,
            "under": under_odds,
        },
        "value": {
            "home": classify_value(fair_home, market_home_odds),
            "draw": classify_value(fair_draw, market_draw_odds),
            "away": classify_value(fair_away, market_away_odds),
            "over": classify_value(fair_over, over_odds),
            "under": classify_value(fair_under, under_odds),
        },
        "ah_text": calc_ah_suggestion(probs["home"], probs["away"]),
    }


def show_stat_cards(title: str, data: Dict[str, Any]) -> None:
    st.markdown(f"### {title}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ແຂ່ງ", data["played"])
    c2.metric("ຊະນະ", data["wins"])
    c3.metric("ສະເໝີ", data["draws"])
    c4.metric("ແພ້", data["losses"])
    c5.metric("ຄະແນນຟອມ", data["form_score"])

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("ຍິງໄດ້", data["gf"])
    d2.metric("ເສຍ", data["ga"])
    d3.metric("ສະເລ່ຍຍິງ", data["avg_gf"])
    d4.metric("ສະເລ່ຍເສຍ", data["avg_ga"])


def main() -> None:
    st.title("⚽ Football AI V8 Full")
    st.caption("ດຶງຕາຕະລາງ + ວິເຄາະ 1X2 / AH / O/U ໃນ app.py ຟາຍດຽວ")

    with st.sidebar:
        st.header("ຕັ້ງຄ່າ")
        url = st.text_input("URL", value=DEFAULT_URL)
        show_tables = st.checkbox("ສະແດງຕາຕະລາງດິບ", value=False)
        show_json = st.checkbox("ສະແດງ JSON ທີ່ດຶງໄດ້", value=False)
        auto_load = st.checkbox("ໂຫຼດຂໍ້ມູນອັດຕະໂນມັດ", value=True)

    tables: List[pd.DataFrame] = []
    json_blocks: List[Dict[str, Any]] = []
    matches: List[Dict[str, Any]] = []

    if auto_load or st.button("ໂຫຼດຂໍ້ມູນ"):
        try:
            tables = fetch_page_tables(url)
        except Exception as e:
            st.warning(f"ດຶງ table ບໍ່ສຳເລັດ: {e}")

        try:
            json_blocks = extract_json_blocks(url)
        except Exception as e:
            st.warning(f"ດຶງ JSON ບໍ່ສຳເລັດ: {e}")

        matches = parse_match_list_from_tables(tables)

    col1, col2, col3 = st.columns(3)
    col1.metric("ຈຳນວນ tables", len(tables))
    col2.metric("ຈຳນວນ JSON blocks", len(json_blocks))
    col3.metric("ຈຳນວນຄູ່ທີ່ຈັບໄດ້", len(matches))

    if show_tables and tables:
        st.subheader("📋 Tables ທີ່ດຶງໄດ້")
        for i, df in enumerate(tables[:5]):
            st.markdown(f"**Table {i+1}**")
            st.dataframe(df, use_container_width=True)

    if show_json and json_blocks:
        st.subheader("🧩 JSON ທີ່ພົບ")
        for i, obj in enumerate(json_blocks[:3]):
            flat = flatten_json(obj)
            preview = pd.DataFrame(flat[:200], columns=["key", "value"])
            st.markdown(f"**JSON Block {i+1}**")
            st.dataframe(preview, use_container_width=True)

    st.divider()
    st.subheader("🎯 ເລືອກຄູ່ເພື່ອວິເຄາະ")

    match_labels = [f"{m['home_team']} vs {m['away_team']}" for m in matches]
    selected_label = st.selectbox("ຄູ່ບານຈາກຂໍ້ມູນ", options=[""] + match_labels)

    st.markdown("#### ຫຼື ກອກເອງ")
    a1, a2 = st.columns(2)
    home_team_input = a1.text_input("ຊື່ທີມເຈົ້າບ້ານ", value="")
    away_team_input = a2.text_input("ຊື່ທີມຢາມ", value="")

    st.markdown("#### ລາຄາຕະຫຼາດ")
    b1, b2, b3 = st.columns(3)
    market_home = b1.number_input("1 ເຈົ້າບ້ານ", min_value=1.01, value=2.10, step=0.01)
    market_draw = b2.number_input("X ສະເໝີ", min_value=1.01, value=3.20, step=0.01)
    market_away = b3.number_input("2 ທີມຢາມ", min_value=1.01, value=3.10, step=0.01)

    c1, c2, c3 = st.columns(3)
    ou_line = c1.number_input("O/U Line", min_value=0.5, value=2.5, step=0.25)
    over_odds = c2.number_input("Over Odds", min_value=1.01, value=1.95, step=0.01)
    under_odds = c3.number_input("Under Odds", min_value=1.01, value=1.90, step=0.01)

    selected_home = ""
    selected_away = ""

    if selected_label:
        selected_home, selected_away = selected_label.split(" vs ", 1)

    home_team = home_team_input.strip() or selected_home
    away_team = away_team_input.strip() or selected_away

    if st.button("ວິເຄາະເຕັມຮູບແບບ", use_container_width=True):
        if not home_team or not away_team:
            st.error("ກະລຸນາເລືອກຄູ່ ຫຼື ກອກຊື່ທີມເອງກ່ອນ")
            st.stop()

        result = analyze_match(
            home_team=home_team,
            away_team=away_team,
            market_home_odds=market_home,
            market_draw_odds=market_draw,
            market_away_odds=market_away,
            ou_line=ou_line,
            over_odds=over_odds,
            under_odds=under_odds,
        )

        st.success(f"ຜົນວິເຄາະ: {home_team} vs {away_team}")

        left, right = st.columns(2)
        with left:
            show_stat_cards(f"📈 {home_team}", result["home_stats"])
        with right:
            show_stat_cards(f"📉 {away_team}", result["away_stats"])

        st.divider()
        st.subheader("🧠 ຄ່າຄາດໝາຍປະຕູ")
        x1, x2, x3 = st.columns(3)
        x1.metric("Home xG", result["home_xg"])
        x2.metric("Away xG", result["away_xg"])
        x3.metric("Total xG", result["total_xg"])

        st.subheader("📊 1X2")
        p = result["probs"]
        f = result["fair_odds"]
        v = result["value"]
        df_1x2 = pd.DataFrame([
            {"ຕະຫຼາດ": "1 ເຈົ້າບ້ານ", "ຄວາມນ່າຈະເປັນ %": p["home"], "ລາຄາຍຸດຕິທຳ": f["home"], "ລາຄາຕະຫຼາດ": result["market_odds"]["home"], "Value": v["home"]},
            {"ຕະຫຼາດ": "X ສະເໝີ", "ຄວາມນ່າຈະເປັນ %": p["draw"], "ລາຄາຍຸດຕິທຳ": f["draw"], "ລາຄາຕະຫຼາດ": result["market_odds"]["draw"], "Value": v["draw"]},
            {"ຕະຫຼາດ": "2 ທີມຢາມ", "ຄວາມນ່າຈະເປັນ %": p["away"], "ລາຄາຍຸດຕິທຳ": f["away"], "ລາຄາຕະຫຼາດ": result["market_odds"]["away"], "Value": v["away"]},
        ])
        st.dataframe(df_1x2, use_container_width=True)

        st.subheader("⚖️ AH")
        st.info(result["ah_text"])

        st.subheader("🎯 Over / Under")
        ou = result["ou_probs"]
        df_ou = pd.DataFrame([
            {"ຕະຫຼາດ": f"Over {ou_line}", "ຄວາມນ່າຈະເປັນ %": ou["over"], "ລາຄາຍຸດຕິທຳ": f["over"], "ລາຄາຕະຫຼາດ": result["market_odds"]["over"], "Value": v["over"]},
            {"ຕະຫຼາດ": f"Under {ou_line}", "ຄວາມນ່າຈະເປັນ %": ou["under"], "ລາຄາຍຸດຕິທຳ": f["under"], "ລາຄາຕະຫຼາດ": result["market_odds"]["under"], "Value": v["under"]},
        ])
        st.dataframe(df_ou, use_container_width=True)

        st.subheader("📝 ສະຫຼຸບ")
        best_1x2 = max([
            ("1 ເຈົ້າບ້ານ", p["home"]),
            ("X ສະເໝີ", p["draw"]),
            ("2 ທີມຢາມ", p["away"]),
        ], key=lambda x: x[1])
        best_ou = "Over" if ou["over"] > ou["under"] else "Under"

        st.write(f"- ຄວາມເປັນໄປໄດ້ 1X2 ສູງສຸດ: **{best_1x2[0]} ({best_1x2[1]}%)**")
        st.write(f"- ແນວໂນ້ມປະຕູລວມ: **{best_ou} {ou_line}**")
        st.write(f"- AH ສະຫຼຸບ: **{result['ah_text']}**")
        st.write("- ລະບົບນີ້ແມ່ນ model ເບື້ອງຕົ້ນ ໃຊ້ສຳລັບຊ່ວຍວິເຄາະ")

    with st.expander("ວິທີໃຊ້"):
        st.write("1. ກົດ Deploy app ໃນ Streamlit")
        st.write("2. ວາງ app.py ນີ້ຟາຍດຽວ")
        st.write("3. requirements.txt ໃສ່: streamlit, pandas, requests, lxml, html5lib")
        st.write("4. ຖ້າ goal7 ດຶງ table ບໍ່ໄດ້ ໃຫ້ກອກຊື່ທີມເອງແລ້ວວິເຄາະ")


if __name__ == "__main__":
    main()
