import re
import json
import math
from typing import Any, Dict, List, Optional

import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Football AI V11 Full", layout="wide")

DEFAULT_URL = "https://goal7.co/"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

# =========================
# helper
# =========================
def safe_text(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()

def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        s = str(x).replace(",", "").strip()
        return float(s)
    except Exception:
        return default

def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def looks_like_team_name(text: str) -> bool:
    t = safe_text(text)
    if len(t) < 2:
        return False
    bad = [
        "บอลสด", "ราคา", "วิเคราะห์", "ตาราง", "ผลบอล", "goal", "login",
        "register", "menu", "home", "live", "stats", "javascript"
    ]
    low = t.lower()
    return not any(b in low for b in bad)

def calc_implied_prob(odd: float) -> float:
    if odd <= 0:
        return 0.0
    return 1.0 / odd

def analyze_value(home_odd: float, draw_odd: float, away_odd: float) -> Dict[str, Any]:
    p1 = calc_implied_prob(home_odd)
    px = calc_implied_prob(draw_odd)
    p2 = calc_implied_prob(away_odd)
    s = p1 + px + p2
    if s <= 0:
        return {"margin_pct": 0.0, "best": "-"}
    p1n = p1 / s
    pxn = px / s
    p2n = p2 / s
    probs = {"Home": p1n, "Draw": pxn, "Away": p2n}
    best = max(probs, key=probs.get)
    return {
        "margin_pct": round((s - 1.0) * 100, 2),
        "home_prob_pct": round(p1n * 100, 2),
        "draw_prob_pct": round(pxn * 100, 2),
        "away_prob_pct": round(p2n * 100, 2),
        "best": best,
    }

# =========================
# fetch
# =========================
def fetch_direct(url: str, timeout: int = 20) -> requests.Response:
    return requests.get(url, headers=UA, timeout=timeout)

def fetch_allorigins(url: str, timeout: int = 30) -> requests.Response:
    proxy_url = "https://api.allorigins.win/raw?url=" + requests.utils.quote(url, safe="")
    return requests.get(proxy_url, headers=UA, timeout=timeout)

def fetch_codetabs(url: str, timeout: int = 30) -> requests.Response:
    proxy_url = "https://api.codetabs.com/v1/proxy/?quest=" + requests.utils.quote(url, safe="")
    return requests.get(proxy_url, headers=UA, timeout=timeout)

def fetch_html(url: str, mode: str, logs: List[str]) -> str:
    methods = []
    if mode == "direct":
        methods = [("direct", fetch_direct)]
    elif mode == "allorigins":
        methods = [("allorigins", fetch_allorigins)]
    elif mode == "codetabs":
        methods = [("codetabs", fetch_codetabs)]
    else:
        methods = [
            ("direct", fetch_direct),
            ("allorigins", fetch_allorigins),
            ("codetabs", fetch_codetabs),
        ]

    last_err = ""
    for name, fn in methods:
        try:
            logs.append(f"เริ่มดึงข้อมูล: {url}")
            logs.append(f"โหมด: {name}")
            res = fn(url)
            logs.append(f"Status: {res.status_code}")
            logs.append(f"Final URL: {res.url}")
            logs.append(f"Content-Type: {res.headers.get('Content-Type', '')}")
            text = res.text or ""
            logs.append(f"ความยาวข้อความ: {len(text)}")
            if res.status_code == 200 and len(text) > 200:
                return text
            last_err = f"{name} status={res.status_code}"
        except Exception as e:
            last_err = f"{name} error={e}"
            logs.append(last_err)

    raise RuntimeError(f"ດຶງຂໍ້ມູນບໍ່ສຳເລັດ: {last_err}")

# =========================
# parser
# =========================
def extract_tables(html: str) -> List[pd.DataFrame]:
    try:
        tables = pd.read_html(html)
        return tables
    except Exception:
        return []

def extract_json_candidates(html: str) -> List[Any]:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    out = []

    for s in scripts:
        text = s.string or s.get_text() or ""
        text = text.strip()
        if not text:
            continue

        # 1) application/ld+json
        if s.get("type") == "application/ld+json":
            try:
                out.append(json.loads(text))
            except Exception:
                pass

        # 2) generic JS object/array search
        patterns = [
            r'=\s*(\{.*?\});',
            r'=\s*(\[.*?\]);',
            r'JSON\.parse\([\'"](.+?)[\'"]\)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.DOTALL):
                raw = m.group(1)
                try:
                    raw2 = raw.encode("utf-8").decode("unicode_escape")
                except Exception:
                    raw2 = raw
                for candidate in [raw, raw2]:
                    try:
                        out.append(json.loads(candidate))
                    except Exception:
                        pass
    return out

def flatten_json(x: Any, prefix: str = "") -> List[Dict[str, Any]]:
    rows = []
    if isinstance(x, dict):
        row = {}
        for k, v in x.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(flatten_json(v, key))
            else:
                row[key] = v
        if row:
            rows.append(row)
    elif isinstance(x, list):
        for i, item in enumerate(x):
            key = f"{prefix}[{i}]"
            rows.extend(flatten_json(item, key))
    return rows

def extract_text_blocks(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    texts = []

    for tag in soup.find_all(["a", "span", "div", "td", "th", "li"]):
        t = tag.get_text(" ", strip=True)
        if t and len(t) <= 80:
            texts.append(t)

    return unique_keep_order(texts)

def pair_teams_from_texts(texts: List[str]) -> List[Dict[str, str]]:
    clean = [t for t in texts if looks_like_team_name(t)]
    pairs = []

    # หา pattern ที่มี vs
    for t in clean:
        if " vs " in t.lower():
            parts = re.split(r"\bvs\b", t, flags=re.IGNORECASE)
            if len(parts) == 2:
                home = safe_text(parts[0])
                away = safe_text(parts[1])
                if home and away:
                    pairs.append({"home": home, "away": away})

    # fallback: จับคู่ข้อความติดกัน
    for i in range(0, min(len(clean) - 1, 60), 2):
        a = clean[i]
        b = clean[i + 1]
        if a != b and len(a) < 40 and len(b) < 40:
            pairs.append({"home": a, "away": b})

    # remove duplicates
    seen = set()
    out = []
    for p in pairs:
        key = (p["home"], p["away"])
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out[:30]

def extract_odds_from_text(texts: List[str]) -> Dict[str, List[str]]:
    one_x_two = []
    ah = []
    ou = []

    odd_pat = re.compile(r'^\d+(\.\d+)?$')
    ah_pat = re.compile(r'^[+-]?\d+(\.\d+)?$')
    ou_pat = re.compile(r'^(o|u|over|under)\s*\d+(\.\d+)?$', re.IGNORECASE)

    for t in texts:
        s = t.strip()
        if odd_pat.match(s):
            v = safe_float(s)
            if 1.01 <= v <= 30:
                one_x_two.append(s)
        if ah_pat.match(s):
            v = safe_float(s)
            if -5 <= v <= 5:
                ah.append(s)
        if ou_pat.match(s):
            ou.append(s)

    return {
        "one_x_two": one_x_two[:200],
        "ah": ah[:200],
        "ou": ou[:200],
    }

def build_match_rows(team_pairs: List[Dict[str, str]], odds_map: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    odds = odds_map.get("one_x_two", [])
    rows = []

    idx = 0
    for pair in team_pairs:
        home_odd = safe_float(odds[idx], 0.0) if idx < len(odds) else 0.0
        draw_odd = safe_float(odds[idx + 1], 0.0) if idx + 1 < len(odds) else 0.0
        away_odd = safe_float(odds[idx + 2], 0.0) if idx + 2 < len(odds) else 0.0
        idx += 3

        analysis = analyze_value(home_odd, draw_odd, away_odd)
        rows.append({
            "home": pair["home"],
            "away": pair["away"],
            "home_odd": home_odd,
            "draw_odd": draw_odd,
            "away_odd": away_odd,
            "best_side": analysis.get("best", "-"),
            "margin_pct": analysis.get("margin_pct", 0.0),
            "home_prob_pct": analysis.get("home_prob_pct", 0.0),
            "draw_prob_pct": analysis.get("draw_prob_pct", 0.0),
            "away_prob_pct": analysis.get("away_prob_pct", 0.0),
        })
    return rows

def parse_everything(html: str) -> Dict[str, Any]:
    tables = extract_tables(html)
    json_blocks = extract_json_candidates(html)
    text_blocks = extract_text_blocks(html)
    team_pairs = pair_teams_from_texts(text_blocks)
    odds_map = extract_odds_from_text(text_blocks)
    match_rows = build_match_rows(team_pairs, odds_map)

    return {
        "tables": tables,
        "json_blocks": json_blocks,
        "text_blocks": text_blocks,
        "team_pairs": team_pairs,
        "odds_map": odds_map,
        "match_rows": match_rows,
    }

# =========================
# UI
# =========================
st.title("⚽ Football AI V11 Full")
st.caption("parser จริง + proxy + debug log + กันพัง + UI แบบ goal7")

with st.sidebar:
    st.header("ຕັ້ງຄ່າ")
    url = st.text_input("URL", value=DEFAULT_URL)
    mode = st.selectbox(
        "ໂໝດດຶງຂໍ້ມູນ",
        ["auto", "direct", "allorigins", "codetabs"],
        index=0
    )
    show_debug = st.checkbox("ສະແດງ debug log", value=True)
    show_raw_text = st.checkbox("ສະແດງ text blocks", value=False)
    show_json = st.checkbox("ສະແດງ json blocks", value=False)
    run_btn = st.button("ດຶງຂໍ້ມູນ", use_container_width=True)

if "result" not in st.session_state:
    st.session_state.result = None
if "logs" not in st.session_state:
    st.session_state.logs = []
if "error" not in st.session_state:
    st.session_state.error = ""

if run_btn:
    logs: List[str] = []
    st.session_state.error = ""
    st.session_state.result = None

    try:
        html = fetch_html(url, mode, logs)
        result = parse_everything(html)
        result["html"] = html

        st.session_state.result = result
        st.session_state.logs = logs
    except Exception as e:
        st.session_state.error = str(e)
        st.session_state.logs = logs

if st.session_state.error:
    st.error(st.session_state.error)

if show_debug and st.session_state.logs:
    with st.expander("ເບິ່ງ log ການດຶງຂໍ້ມູນ", expanded=True):
        for line in st.session_state.logs:
            st.code(line)

result = st.session_state.result
if result:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ຈຳນວນ tables", len(result["tables"]))
    c2.metric("ຈຳນວນ JSON blocks", len(result["json_blocks"]))
    c3.metric("ຈຳນວນຄູ່ທີ່ຈັບໄດ້", len(result["team_pairs"]))
    c4.metric("ຈຳນວນ rows ວິເຄາະ", len(result["match_rows"]))

    st.subheader("🎯 ຄູ່ບານເພື່ອວິເຄາະ")
    match_rows = result["match_rows"]

    if match_rows:
        df = pd.DataFrame(match_rows)
        st.dataframe(df, use_container_width=True)

        st.subheader("📊 Match Cards")
        for row in match_rows[:20]:
            with st.container(border=True):
                a, b, c = st.columns([3, 3, 2])
                with a:
                    st.markdown(f"**{row['home']}**")
                    st.caption(f"1 = {row['home_odd']}")
                with b:
                    st.markdown(f"**{row['away']}**")
                    st.caption(f"2 = {row['away_odd']}")
                with c:
                    st.markdown(f"**X = {row['draw_odd']}**")
                    st.caption(f"Best: {row['best_side']}")
                    st.caption(f"Margin: {row['margin_pct']}%")
    else:
        st.warning("ດຶງ HTML ໄດ້ແລ້ວ ແຕ່ຍັງ parse ຄູ່ບານບໍ່ອອກ")

    if result["tables"]:
        st.subheader("📋 Tables ທີ່ດຶງໄດ້")
        for i, table in enumerate(result["tables"][:5], start=1):
            st.markdown(f"**Table {i}**")
            st.dataframe(table, use_container_width=True)

    if show_json and result["json_blocks"]:
        st.subheader("🧩 JSON Blocks")
        for i, jb in enumerate(result["json_blocks"][:10], start=1):
            st.markdown(f"**JSON {i}**")
            st.json(jb)

    if show_raw_text:
        st.subheader("📝 Text Blocks")
        st.write(result["text_blocks"][:500])

    st.subheader("🔍 ຂໍ້ມູນດິບ")
    st.write("Title:", BeautifulSoup(result["html"], "html.parser").title.string if BeautifulSoup(result["html"], "html.parser").title else "-")
    st.write("Final URL:", url)
    st.write("Content length:", len(result["html"]))
