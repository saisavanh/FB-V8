import re
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import requests
import pandas as pd
import streamlit as st


# =========================
# Football AI V9 Proxy Full
# app.py ຟາຍດຽວ
# =========================

st.set_page_config(page_title="Football AI V9 Proxy Full", layout="wide")

DEFAULT_URL = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
TIMEOUT = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip()
        text = text.replace(",", "")
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if match:
            return float(match.group())
        return default
    except Exception:
        return default


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_html_direct(url: str) -> Tuple[int, str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_html_proxy_allorigins(url: str) -> Tuple[int, str]:
    try:
        proxy_url = "https://api.allorigins.win/raw?url=" + requests.utils.quote(url, safe="")
        r = requests.get(proxy_url, headers=HEADERS, timeout=TIMEOUT)
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_html_proxy_codetabs(url: str) -> Tuple[int, str]:
    try:
        proxy_url = "https://api.codetabs.com/v1/proxy/?quest=" + requests.utils.quote(url, safe="")
        r = requests.get(proxy_url, headers=HEADERS, timeout=TIMEOUT)
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


def fetch_html(url: str) -> Dict[str, Any]:
    methods = [
        ("direct", fetch_html_direct),
        ("allorigins", fetch_html_proxy_allorigins),
        ("codetabs", fetch_html_proxy_codetabs),
    ]

    logs = []
    for name, func in methods:
        status, text = func(url)
        logs.append({"method": name, "status": status, "length": len(text or "")})

        if status == 200 and text and "403 Forbidden" not in text[:500]:
            return {
                "ok": True,
                "method": name,
                "status": status,
                "html": text,
                "logs": logs,
            }

    return {
        "ok": False,
        "method": "none",
        "status": logs[-1]["status"] if logs else 0,
        "html": "",
        "logs": logs,
    }


def try_read_html_tables(html: str) -> List[pd.DataFrame]:
    try:
        tables = pd.read_html(html)
        clean_tables = []
        for df in tables:
            if df is None or df.empty:
                continue
            df = df.copy()
            df.columns = [clean_text(c) for c in df.columns]
            for col in df.columns:
                df[col] = df[col].astype(str).map(clean_text)
            clean_tables.append(df)
        return clean_tables
    except Exception:
        return []


def extract_json_blocks(html: str) -> List[str]:
    patterns = [
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        r"<script[^>]*>(.*?)</script>",
    ]
    results = []

    for pattern in patterns:
        blocks = re.findall(pattern, html, flags=re.DOTALL | re.IGNORECASE)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if "{" in block or "[" in block:
                results.append(block)

    unique = []
    seen = set()
    for item in results:
        k = item[:500]
        if k not in seen:
            seen.add(k)
            unique.append(item)
    return unique


def extract_match_lines(html: str) -> List[str]:
    text = re.sub(r"<[^>]+>", "\n", html)
    lines = [clean_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    keywords = [
        "vs", "v ", "-", "AH", "O/U", "1X2", "FT", "HT",
        "Home", "Away", "ราคา", "บอลสด", "ลีก", "เวลา"
    ]

    picked = []
    for line in lines:
        score_like = re.search(r"\b\d{1,2}:\d{2}\b", line)
        team_like = len(line.split()) >= 2 and len(line) <= 120
        key_like = any(k.lower() in line.lower() for k in keywords)
        if score_like or key_like or team_like:
            picked.append(line)

    return picked[:300]


def score_table(df: pd.DataFrame) -> int:
    score = 0
    cols = [c.lower() for c in df.columns]
    text_blob = " ".join(cols + df.astype(str).fillna("").head(8).astype(str).agg(" ".join, axis=1).tolist()).lower()

    signals = [
        "1x2", "ah", "o/u", "ou", "over", "under", "home", "away",
        "team", "match", "odd", "odds", "handicap", "ลีก", "เวลา", "ราคา"
    ]
    for s in signals:
        if s in text_blob:
            score += 2

    if 2 <= len(df.columns) <= 15:
        score += 2
    if len(df) >= 2:
        score += 2

    return score


def classify_table(df: pd.DataFrame) -> str:
    text_blob = " ".join([c.lower() for c in df.columns])
    body_blob = " ".join(df.astype(str).fillna("").head(10).astype(str).agg(" ".join, axis=1).tolist()).lower()
    blob = text_blob + " " + body_blob

    if "1x2" in blob or ("home" in blob and "draw" in blob and "away" in blob):
        return "1X2"
    if "ah" in blob or "handicap" in blob or "ต่อ" in blob:
        return "AH"
    if "o/u" in blob or "over" in blob or "under" in blob or "สูง" in blob or "ต่ำ" in blob:
        return "O/U"
    return "ຕາຕະລາງທົ່ວໄປ"


def find_best_tables(tables: List[pd.DataFrame]) -> List[Dict[str, Any]]:
    items = []
    for i, df in enumerate(tables):
        s = score_table(df)
        if s < 3:
            continue
        items.append({
            "index": i,
            "score": s,
            "type": classify_table(df),
            "rows": len(df),
            "cols": len(df.columns),
            "df": df,
        })
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def detect_numeric_columns(df: pd.DataFrame) -> List[str]:
    result = []
    for col in df.columns:
        values = df[col].astype(str).tolist()[:20]
        count_num = 0
        for v in values:
            if re.search(r"-?\d+(\.\d+)?", v):
                count_num += 1
        if count_num >= max(2, len(values) // 3):
            result.append(col)
    return result


def summarize_table(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_cols = detect_numeric_columns(df)
    summary = {
        "rows": len(df),
        "cols": len(df.columns),
        "columns": list(df.columns),
        "numeric_columns": numeric_cols,
        "sample": df.head(5).to_dict(orient="records"),
    }
    return summary


def ai_analyze_table(df: pd.DataFrame, table_type: str) -> str:
    summary = summarize_table(df)
    lines = []

    lines.append(f"ປະເພດຕາຕະລາງ: {table_type}")
    lines.append(f"ຈຳນວນແຖວ: {summary['rows']}")
    lines.append(f"ຈຳນວນຖັນ: {summary['cols']}")

    if summary["numeric_columns"]:
        lines.append("ຖັນທີ່ມີຄ່າໂຕເລກ: " + ", ".join(summary["numeric_columns"]))
    else:
        lines.append("ຍັງບໍ່ພົບຖັນໂຕເລກຊັດເຈນ")

    if table_type == "1X2":
        lines.append("ການອ່ານ 1X2: ເບິ່ງຄ່າ Home / Draw / Away ເພື່ອຫາຝັ່ງທີ່ລາຄາຕ່ຳສຸດ")
        lines.append("ຝັ່ງທີ່ລາຄານ້ອຍກວ່າ ມັກເປັນຝັ່ງທີ່ຕະຫຼາດມອງວ່າເປັນຕໍ່")
    elif table_type == "AH":
        lines.append("ການອ່ານ AH: ເບິ່ງຄ່າຕໍ່/ຮອງ ແລະ ຄ່ານ້ຳ ເພື່ອຫາ value")
        lines.append("ຖ້ານ້ຳຝັ່ງໃດຫຼຸດລົງ ມັກຈະມີແຮງເງິນເຂົ້າຝັ່ງນັ້ນ")
    elif table_type == "O/U":
        lines.append("ການອ່ານ O/U: ເບິ່ງເສັ້ນສູງ/ຕ່ຳ ແລະ ຄ່ານ້ຳຂອງ Over/Under")
        lines.append("ຖ້າ Over ນ້ຳຫຼຸດ ອາດມີແນວໂນ້ມຕະຫຼາດໄປທາງສູງ")
    else:
        lines.append("ຕາຕະລາງນີ້ຍັງບໍ່ຈັດປະເພດໄດ້ຊັດ ແຕ່ຍັງສາມາດນຳໄປກວດສອບຕໍ່ໄດ້")

    return "\n".join(lines)


def infer_match_column(df: pd.DataFrame) -> Optional[str]:
    best_col = None
    best_score = -1

    for col in df.columns:
        values = df[col].astype(str).head(20).tolist()
        score = 0
        for v in values:
            txt = clean_text(v).lower()
            if len(txt) > 5:
                score += 1
            if "vs" in txt or " v " in txt or "-" in txt:
                score += 2
        if score > best_score:
            best_score = score
            best_col = col

    return best_col


def show_logs(fetch_result: Dict[str, Any]) -> None:
    with st.expander("ເບິ່ງ log ການດຶງຂໍ້ມູນ"):
        st.json(fetch_result.get("logs", []))


# =========================
# UI
# =========================

st.title("⚽ Football AI V9 Proxy Full")
st.caption("ດຶງຂໍ້ມູນຜ່ານ proxy ເພື່ອແກ້ 403 ແລະຊ່ວຍອ່ານຕາຕະລາງ 1X2 / AH / O/U")

with st.sidebar:
    st.header("ຕັ້ງຄ່າ")
    input_url = st.text_input("ໃສ່ URL", value=DEFAULT_URL)
    show_html_preview = st.checkbox("ສະແດງ HTML ຕົວຢ່າງ", value=False)
    show_json_blocks = st.checkbox("ສະແດງ JSON blocks", value=False)
    max_tables_to_show = st.slider("ຈຳນວນຕາຕະລາງສູງສຸດ", 1, 20, 8)

col_a, col_b = st.columns([1, 1])

with col_a:
    run_btn = st.button("ດຶງຂໍ້ມູນ", use_container_width=True)

with col_b:
    st.link_button("ເປີດເວັບຕົ້ນທາງ", input_url if is_url(input_url) else DEFAULT_URL, use_container_width=True)

if run_btn:
    if not input_url or not is_url(input_url):
        st.error("ກະລຸນາໃສ່ URL ໃຫ້ຖືກຕ້ອງ")
        st.stop()

    with st.spinner("ກຳລັງດຶງຂໍ້ມູນ..."):
        fetch_result = fetch_html(input_url)

    st.subheader("ສະຖານະການດຶງຂໍ້ມູນ")
    c1, c2, c3 = st.columns(3)
    c1.metric("ສຳເລັດ", "ແມ່ນ" if fetch_result["ok"] else "ບໍ່")
    c2.metric("ວິທີທີ່ໃຊ້", fetch_result["method"])
    c3.metric("Status", fetch_result["status"])

    show_logs(fetch_result)

    if not fetch_result["ok"]:
        st.error("ດຶງຂໍ້ມູນບໍ່ສຳເລັດ ລອງ URL ອື່ນ ຫຼື ລອງໃໝ່ອີກຄັ້ງ")
        st.stop()

    html = fetch_result["html"]

    if show_html_preview:
        with st.expander("HTML ຕົວຢ່າງ 2000 ຕົວອັກສອນ"):
            st.code(html[:2000], language="html")

    with st.spinner("ກຳລັງອ່ານຕາຕະລາງ..."):
        tables = try_read_html_tables(html)
        json_blocks = extract_json_blocks(html)
        raw_lines = extract_match_lines(html)

    st.subheader("ຜົນການອ່ານເບື້ອງຕົ້ນ")
    r1, r2, r3 = st.columns(3)
    r1.metric("ຈຳນວນ tables", len(tables))
    r2.metric("ຈຳນວນ JSON blocks", len(json_blocks))
    r3.metric("ຈຳນວນບັນທັດທີ່ຈັບໄດ້", len(raw_lines))

    if show_json_blocks and json_blocks:
        with st.expander("JSON blocks"):
            for i, block in enumerate(json_blocks[:10], 1):
                st.markdown(f"**Block {i}**")
                st.code(block[:3000], language="json")

    if raw_lines:
        with st.expander("ບັນທັດຂໍ້ມູນທີ່ຈັບໄດ້"):
            for line in raw_lines[:120]:
                st.write("- " + line)

    best_tables = find_best_tables(tables)

    st.subheader("🎯 ຕາຕະລາງທີ່ນ່າຈະໃຊ້ງານໄດ້")
    if not best_tables:
        st.warning("ຍັງບໍ່ພົບຕາຕະລາງທີ່ອ່ານໄດ້ຊັດເຈນ ແຕ່ proxy ທຳງານແລ້ວ")
    else:
        for item in best_tables[:max_tables_to_show]:
            st.markdown(f"### ຕາຕະລາງ #{item['index']} | {item['type']}")
            info1, info2, info3, info4 = st.columns(4)
            info1.metric("score", item["score"])
            info2.metric("rows", item["rows"])
            info3.metric("cols", item["cols"])
            info4.metric("type", item["type"])

            df = item["df"]
            st.dataframe(df, use_container_width=True)

            with st.expander("AI ວິເຄາະຕາຕະລາງນີ້"):
                st.text(ai_analyze_table(df, item["type"]))

            with st.expander("ສະຫຼຸບໂຄງສ້າງ"):
                st.json(summarize_table(df))

    st.subheader("📌 ເລືອກຄູ່ເພື່ອວິເຄາະ")
    if best_tables:
        candidate_labels = []
        candidate_map = {}

        for item in best_tables[:max_tables_to_show]:
            df = item["df"]
            match_col = infer_match_column(df)
            if match_col:
                values = df[match_col].astype(str).head(30).tolist()
                for idx, v in enumerate(values):
                    label = clean_text(v)
                    if len(label) >= 4:
                        key = f"{item['type']} | table {item['index']} | row {idx} | {label}"
                        candidate_labels.append(key)
                        candidate_map[key] = {
                            "table_index": item["index"],
                            "row_index": idx,
                            "label": label,
                            "type": item["type"],
                        }

        if candidate_labels:
            selected = st.selectbox("ເລືອກລາຍການ", candidate_labels)
            selected_info = candidate_map[selected]
            st.success(f"ເລືອກແລ້ວ: {selected_info['label']}")

            selected_table = None
            for item in best_tables:
                if item["index"] == selected_info["table_index"]:
                    selected_table = item["df"]
                    break

            if selected_table is not None:
                row_idx = selected_info["row_index"]
                if row_idx < len(selected_table):
                    row_data = selected_table.iloc[row_idx].to_dict()
                    st.markdown("#### ຂໍ້ມູນແຖວທີ່ເລືອກ")
                    st.json({k: clean_text(v) for k, v in row_data.items()})

                    st.markdown("#### ວິເຄາະແບບໄວ")
                    analysis_lines = []
                    analysis_lines.append(f"ປະເພດຕະຫຼາດ: {selected_info['type']}")
                    analysis_lines.append(f"ຄູ່ທີ່ເລືອກ: {selected_info['label']}")

                    numeric_items = []
                    for k, v in row_data.items():
                        num = safe_float(v, default=math.nan)
                        if not math.isnan(num):
                            numeric_items.append((k, num))

                    if numeric_items:
                        numeric_items_sorted = sorted(numeric_items, key=lambda x: x[1])
                        analysis_lines.append("ຄ່າໂຕເລກທີ່ພົບ:")
                        for k, v in numeric_items_sorted[:10]:
                            analysis_lines.append(f"- {k}: {v}")

                        analysis_lines.append("ຫຼັກຄິດ: ຄ່າທີ່ຕ່ຳກວ່າມັກຈະໝາຍເຖິງຝັ່ງທີ່ຖືກມອງສູງກວ່າ")
                    else:
                        analysis_lines.append("ຍັງບໍ່ພົບຄ່າໂຕເລກຊັດເຈນໃນແຖວນີ້")

                    if selected_info["type"] == "AH":
                        analysis_lines.append("AH: ໃຫ້ເບິ່ງຝັ່ງຕໍ່/ຮອງ ແລະ ການໄຫຼຂອງນ້ຳ")
                    elif selected_info["type"] == "O/U":
                        analysis_lines.append("O/U: ໃຫ້ເບິ່ງເສັ້ນສູງຕ່ຳ ແລະ ຄ່ານ້ຳ Over/Under")
                    elif selected_info["type"] == "1X2":
                        analysis_lines.append("1X2: ປຽບທຽບ Home / Draw / Away ເພື່ອຫາຝັ່ງນ່າສົນໃຈ")

                    st.text("\n".join(analysis_lines))
        else:
            st.info("ຍັງບໍ່ພົບລາຍການຄູ່ແບບຊັດເຈນໃຫ້ເລືອກ")

    st.subheader("📦 ຕາຕະລາງທັງໝົດ")
    if tables:
        for i, df in enumerate(tables[:max_tables_to_show], 1):
            with st.expander(f"table {i} | rows={len(df)} | cols={len(df.columns)}"):
                st.dataframe(df, use_container_width=True)
    else:
        st.warning("ບໍ່ພົບ table ຈາກ HTML")

else:
    st.info("ກົດປຸ່ມ 'ດຶງຂໍ້ມູນ' ເພື່ອເລີ່ມ")
    st.code(DEFAULT_URL)
