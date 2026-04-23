import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# =========================
# Football AI V10
# parser จริง + proxy + debug log + กันพัง
# =========================

st.set_page_config(page_title="Football AI V10", page_icon="⚽", layout="wide")

DEFAULT_URL = "https://goal7.co/"
TIMEOUT = 25
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PROXY_MODES = {
    "direct": lambda url: url,
    "allorigins": lambda url: f"https://api.allorigins.win/raw?url={quote(url, safe='')}",
    "codetabs": lambda url: f"https://api.codetabs.com/v1/proxy?quest={quote(url, safe='')}",
    "corsproxy": lambda url: f"https://corsproxy.io/?{quote(url, safe='')}",
}


@dataclass
class FetchResult:
    ok: bool
    mode: str
    source_url: str
    final_url: str
    status_code: int
    html: str
    error: str
    logs: List[str]


@dataclass
class MatchRow:
    league: str = ""
    home: str = ""
    away: str = ""
    score: str = ""
    time_text: str = ""
    detail: str = ""
    raw_text: str = ""


@dataclass
class OddsRow:
    market: str = ""
    label: str = ""
    home: str = ""
    draw: str = ""
    away: str = ""
    over: str = ""
    under: str = ""
    handicap: str = ""
    source: str = ""


# ---------- helpers ----------

def add_log(logs: List[str], message: str) -> None:
    logs.append(message)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8,lo;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def fetch_once(url: str, mode: str) -> FetchResult:
    logs: List[str] = []
    final_url = PROXY_MODES[mode](url)
    add_log(logs, f"เริ่มดึงข้อมูล: {url}")
    add_log(logs, f"โหมด: {mode}")
    add_log(logs, f"URL ที่เรียกจริง: {final_url}")
    try:
        resp = requests.get(final_url, headers=HEADERS, timeout=TIMEOUT)
        status = resp.status_code
        text = resp.text or ""
        add_log(logs, f"HTTP status: {status}")
        add_log(logs, f"ขนาดข้อความ: {len(text)} ตัวอักษร")
        if status != 200:
            return FetchResult(False, mode, url, final_url, status, text, f"HTTP {status}", logs)
        if "403 Forbidden" in text[:3000]:
            return FetchResult(False, mode, url, final_url, status, text, "เจอ 403 Forbidden ในเนื้อหา", logs)
        return FetchResult(True, mode, url, final_url, status, text, "", logs)
    except Exception as e:
        add_log(logs, f"exception: {type(e).__name__}: {e}")
        return FetchResult(False, mode, url, final_url, 0, "", f"{type(e).__name__}: {e}", logs)


@st.cache_data(ttl=180, show_spinner=False)
def fetch_html(url: str, preferred_mode: str) -> FetchResult:
    tried: List[str] = []
    order = [preferred_mode] + [m for m in PROXY_MODES if m != preferred_mode]
    merged_logs: List[str] = []
    for mode in order:
        tried.append(mode)
        result = fetch_once(url, mode)
        merged_logs.extend(result.logs)
        if result.ok and len(result.html) > 200:
            result.logs = merged_logs + [f"สำเร็จด้วยโหมด: {mode}"]
            return result
        merged_logs.append(f"ไม่สำเร็จด้วยโหมด {mode}: {result.error}")
    return FetchResult(False, tried[-1], url, PROXY_MODES[tried[-1]](url), 0, "", "ลองทุกโหมดแล้วไม่สำเร็จ", merged_logs)


# ---------- parser จริง ----------

def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def parse_tables(html: str) -> List[pd.DataFrame]:
    tables: List[pd.DataFrame] = []
    try:
        raw_tables = pd.read_html(html)
        for df in raw_tables:
            df = df.fillna("")
            df.columns = [clean_text(c) for c in df.columns]
            tables.append(df)
    except Exception:
        pass
    return tables


def extract_json_blocks(html: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    patterns = [
        r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>",
        r"__NEXT_DATA__\s*=\s*(\{.*?\})\s*</script>",
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        r"window\.__NUXT__\s*=\s*(\{.*?\});",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html, flags=re.S | re.I):
            raw = m.group(1).strip()
            try:
                obj = json.loads(raw)
                blocks.append(obj)
            except Exception:
                continue
    return blocks


def parse_match_rows(html: str) -> List[MatchRow]:
    soup = soup_from_html(html)
    rows: List[MatchRow] = []

    selectors = [
        "tr",
        ".match-row",
        ".match-item",
        ".list-item",
        ".live-list li",
        ".event-item",
        ".score-row",
        ".panel-body li",
    ]

    seen = set()
    for sel in selectors:
        for node in soup.select(sel):
            text = clean_text(node.get_text(" ", strip=True))
            if len(text) < 12:
                continue
            if text in seen:
                continue
            seen.add(text)

            teams = re.findall(r"([A-Za-zÀ-ÿก-๙ກ-ໝ0-9\.\- ]{2,})", text)
            score = ""
            m_score = re.search(r"\b(\d{1,2}\s*[-:]\s*\d{1,2})\b", text)
            if m_score:
                score = clean_text(m_score.group(1))

            time_text = ""
            m_time = re.search(r"\b(\d{1,2}:\d{2}|FT|HT|LIVE|\d{1,3}\+?\d*')\b", text, flags=re.I)
            if m_time:
                time_text = clean_text(m_time.group(1))

            home = ""
            away = ""
            if " vs " in text.lower():
                parts = re.split(r"\bvs\b", text, flags=re.I)
                if len(parts) >= 2:
                    home, away = clean_text(parts[0]), clean_text(parts[1])
            elif score:
                parts = re.split(r"\b\d{1,2}\s*[-:]\s*\d{1,2}\b", text, maxsplit=1)
                if len(parts) >= 2:
                    left = clean_text(parts[0])
                    right = clean_text(parts[1])
                    # เอาชื่อท้ายซ้ายและต้นขวา
                    home = clean_text(left.split()[-3:]) if isinstance(left.split()[-3:], list) else left
                    away = clean_text(" ".join(right.split()[:3]))

            if not home and not away and len(text) < 180:
                parts = [p.strip() for p in re.split(r"  +|\|", text) if p.strip()]
                if len(parts) >= 2:
                    home, away = parts[0], parts[1]

            rows.append(MatchRow(home=home, away=away, score=score, time_text=time_text, raw_text=text))

    # ตัดซ้ำและเก็บที่ดูมีประโยชน์
    compact: List[MatchRow] = []
    seen2 = set()
    for r in rows:
        key = (r.home, r.away, r.score, r.time_text, r.raw_text[:80])
        if key in seen2:
            continue
        seen2.add(key)
        if r.home or r.away or r.score:
            compact.append(r)
    return compact[:200]


def parse_odds_rows(html: str) -> List[OddsRow]:
    soup = soup_from_html(html)
    rows: List[OddsRow] = []
    texts: List[str] = []
    for node in soup.select("table tr, .odds-row, .market-row, .rate-row, .ah-row, .ou-row"):
        text = clean_text(node.get_text(" ", strip=True))
        if text:
            texts.append(text)

    patterns = [
        ("1X2", r"(.+?)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)"),
        ("OU", r"(O/U|Over/Under|สูงต่ำ)\s*([0-9\.\-/]+)?\s*(\d+\.\d+)\s*(\d+\.\d+)"),
        ("AH", r"(AH|Handicap|แฮนดิแคป)\s*([\-\+0-9\./]+)?\s*(\d+\.\d+)\s*(\d+\.\d+)"),
    ]
    for text in texts:
        for market, pattern in patterns:
            m = re.search(pattern, text, flags=re.I)
            if not m:
                continue
            if market == "1X2":
                rows.append(OddsRow(market=market, label=clean_text(m.group(1)), home=m.group(2), draw=m.group(3), away=m.group(4), source=text))
            elif market == "OU":
                rows.append(OddsRow(market=market, handicap=clean_text(m.group(2)), over=m.group(3), under=m.group(4), source=text))
            else:
                rows.append(OddsRow(market=market, handicap=clean_text(m.group(2)), home=m.group(3), away=m.group(4), source=text))
    return rows[:200]


def dataframe_from_matches(rows: List[MatchRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in rows]) if rows else pd.DataFrame(columns=["league", "home", "away", "score", "time_text", "detail", "raw_text"])


def dataframe_from_odds(rows: List[OddsRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in rows]) if rows else pd.DataFrame(columns=["market", "label", "home", "draw", "away", "over", "under", "handicap", "source"])


# ---------- UI ----------
st.title("⚽ Football AI V10")
st.caption("parser จริง + proxy + debug log + กันพัง")

col1, col2 = st.columns([3, 2])
with col1:
    url = st.text_input("ໃສ່ URL", value=DEFAULT_URL)
with col2:
    proxy_mode = st.selectbox("ໂໝດ proxy", list(PROXY_MODES.keys()), index=1)

run = st.button("ດຶງຂໍ້ມູນ", use_container_width=True)

if run:
    result = fetch_html(url, proxy_mode)

    st.subheader("ສະຖານະການດຶງຂໍ້ມູນ")
    a, b, c = st.columns(3)
    a.metric("ສຳເລັດ", "ແມ່ນ" if result.ok else "ບໍ່")
    b.metric("ວິທີທີ່ໃຊ້", result.mode)
    c.metric("Status", result.status_code)

    with st.expander("ເບິ່ງ log ການດຶງຂໍ້ມູນ", expanded=True):
        for line in result.logs:
            st.code(line, language="text")

    if not result.ok:
        st.error(f"ດຶງບໍ່ສຳເລັດ: {result.error}")
        st.stop()

    html = result.html
    tables = parse_tables(html)
    json_blocks = extract_json_blocks(html)
    match_rows = parse_match_rows(html)
    odds_rows = parse_odds_rows(html)

    st.subheader("ຜົນການອ່ານເບື້ອງຕົ້ນ")
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("ຈຳນວນ tables", len(tables))
    x2.metric("ຈຳນວນ JSON blocks", len(json_blocks))
    x3.metric("ຈຳນວນຄູ່ທີ່ຈັບໄດ້", len(match_rows))
    x4.metric("ຈຳນວນ odds ທີ່ຈັບໄດ້", len(odds_rows))

    st.subheader("ເລືອກຄູ່ເພື່ອວິເຄາະ")
    df_matches = dataframe_from_matches(match_rows)
    if not df_matches.empty:
        st.dataframe(df_matches, use_container_width=True)
    else:
        st.warning("ຍັງບໍ່ຈັບຄູ່ໄດ້ຊັດເຈນ")

    st.subheader("ຂໍ້ມູນ odds")
    df_odds = dataframe_from_odds(odds_rows)
    if not df_odds.empty:
        st.dataframe(df_odds, use_container_width=True)
    else:
        st.info("ຍັງບໍ່ພົບ odds ແບບທີ່ parser ຈັບໄດ້")

    st.subheader("HTML preview")
    st.code(html[:5000], language="html")

    if json_blocks:
        st.subheader("JSON block ตัวอย่าง")
        st.json(json_blocks[0])

st.markdown("---")
st.caption("ຖ້າ goal7 ບລັອກການເຂົ້າເຖິງ ໃຫ້ລອງ allorigins, codetabs, corsproxy ຫຼືໃສ່ URL ໜ້າຍ່ອຍທີ່ມີຕາຕະລາງໂດຍກົງ")

