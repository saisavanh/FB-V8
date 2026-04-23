import json
import re
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# =========================================================
# Football AI V10 FIX FULL
# - กันพัง
# - รองรับ direct / proxy
# - มี debug log
# - พยายามอ่าน tables / json scripts / title / text
# =========================================================

st.set_page_config(page_title="Football AI V10 FIX", layout="wide")

# -----------------------------
# CONFIG
# -----------------------------
DEFAULT_URL = "https://goal7.co/"
DEFAULT_TIMEOUT = 25

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7,lo;q=0.6",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.google.com/",
}

# -----------------------------
# HELPERS
# -----------------------------
def add_log(logs: List[str], text: str) -> None:
    logs.append(text)

def safe_get_secrets(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def clean_text(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def build_proxy_url(mode: str, target_url: str) -> str:
    """
    mode:
    - direct
    - allorigins
    - codetabs
    """
    if mode == "allorigins":
        return f"https://api.allorigins.win/raw?url={target_url}"
    if mode == "codetabs":
        return f"https://api.codetabs.com/v1/proxy?quest={target_url}"
    return target_url

def build_requests_proxies() -> Optional[Dict[str, str]]:
    """
    รองรับใส่ proxy ผ่าน Streamlit secrets เช่น:
    HTTP_PROXY="http://user:pass@host:port"
    HTTPS_PROXY="http://user:pass@host:port"
    """
    http_proxy = safe_get_secrets("HTTP_PROXY", "")
    https_proxy = safe_get_secrets("HTTPS_PROXY", "")
    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy
    return proxies if proxies else None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_html(
    url: str,
    mode: str,
    timeout: int,
    use_custom_proxy: bool,
) -> Tuple[Optional[str], Dict[str, Any]]:
    logs: List[str] = []
    meta: Dict[str, Any] = {
        "ok": False,
        "status_code": None,
        "final_url": "",
        "mode": mode,
        "error": "",
        "content_type": "",
        "content_length": 0,
        "logs": logs,
    }

    try:
        final_url = build_proxy_url(mode, url)
        meta["final_url"] = final_url
        add_log(logs, f"เริ่มดึงข้อมูล: {url}")
        add_log(logs, f"โหมด: {mode}")
        add_log(logs, f"URL ที่เรียกจริง: {final_url}")

        proxies = build_requests_proxies() if use_custom_proxy else None
        if proxies:
            add_log(logs, "ใช้ custom proxy จาก secrets")

        response = requests.get(
            final_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            proxies=proxies,
        )

        meta["status_code"] = response.status_code
        meta["content_type"] = response.headers.get("Content-Type", "")
        meta["content_length"] = len(response.text or "")

        add_log(logs, f"Status: {response.status_code}")
        add_log(logs, f"Content-Type: {meta['content_type']}")
        add_log(logs, f"ความยาวข้อความ: {meta['content_length']}")

        if response.status_code != 200:
            meta["error"] = f"HTTP {response.status_code}"
            add_log(logs, f"ดึงไม่สำเร็จ: HTTP {response.status_code}")
            return None, meta

        html = response.text
        if not html or not html.strip():
            meta["error"] = "response ว่าง"
            add_log(logs, "response ว่าง")
            return None, meta

        meta["ok"] = True
        add_log(logs, "ดึงข้อมูลสำเร็จ")
        return html, meta

    except Exception as e:
        meta["error"] = str(e)
        add_log(logs, f"Exception: {e}")
        return None, meta

def parse_tables_from_html(html: str, logs: List[str]) -> List[pd.DataFrame]:
    tables: List[pd.DataFrame] = []
    try:
        found = pd.read_html(StringIO(html))
        for i, df in enumerate(found):
            if isinstance(df, pd.DataFrame) and not df.empty:
                tables.append(df)
        add_log(logs, f"อ่านตารางได้: {len(tables)}")
    except Exception as e:
        add_log(logs, f"อ่าน tables ไม่สำเร็จ: {e}")
    return tables

def extract_json_blocks(html: str, logs: List[str]) -> List[Any]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Any] = []

    scripts = soup.find_all("script")
    for script in scripts:
        script_type = (script.get("type") or "").strip().lower()
        content = script.string or script.text or ""
        content = content.strip()
        if not content:
            continue

        # JSON-LD
        if "ld+json" in script_type:
            try:
                obj = json.loads(content)
                results.append(obj)
                continue
            except Exception:
                pass

        # พยายามหา object / array ใหญ่ใน script
        if content.startswith("{") or content.startswith("["):
            try:
                obj = json.loads(content)
                results.append(obj)
                continue
            except Exception:
                pass

    add_log(logs, f"เจอ JSON blocks: {len(results)}")
    return results

def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string if soup.title and soup.title.string else ""
    return clean_text(title)

def extract_visible_text(html: str, max_chars: int = 2500) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text(separator=" ")
    text = clean_text(text)
    return text[:max_chars]

def find_candidate_match_links(html: str, base_url: str, logs: List[str]) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = clean_text(a.get_text(" ", strip=True)).lower()

        if not href:
            continue

        signal_words = [
            "vs", "บอลสด", "ฟุตบอล", "match", "fixture", "ลีก",
            "พรีเมียร์ลีก", "score", "live", "odds", "analysis"
        ]

        href_lower = href.lower()
        if any(w in href_lower for w in signal_words) or any(w in text for w in signal_words):
            if href.startswith("http://") or href.startswith("https://"):
                links.append(href)
            elif href.startswith("/"):
                root = re.match(r"^(https?://[^/]+)", base_url)
                if root:
                    links.append(root.group(1) + href)

    deduped = []
    seen = set()
    for x in links:
        if x not in seen:
            deduped.append(x)
            seen.add(x)

    add_log(logs, f"ลิงก์ที่น่าจะเกี่ยวกับคู่บอล: {len(deduped)}")
    return deduped[:30]

def summarize_json_blocks(json_blocks: List[Any]) -> List[Dict[str, Any]]:
    summary = []
    for idx, item in enumerate(json_blocks[:10], start=1):
        if isinstance(item, dict):
            summary.append({
                "ลำดับ": idx,
                "ชนิด": "dict",
                "keys": list(item.keys())[:20],
            })
        elif isinstance(item, list):
            summary.append({
                "ลำดับ": idx,
                "ชนิด": "list",
                "จำนวนสมาชิก": len(item),
            })
        else:
            summary.append({
                "ลำดับ": idx,
                "ชนิด": type(item).__name__,
            })
    return summary

def analyze_tables(tables: List[pd.DataFrame]) -> Dict[str, Any]:
    result = {
        "total_tables": len(tables),
        "rows_total": 0,
        "cols_total": 0,
        "non_empty_tables": 0,
        "preview_shapes": [],
    }

    for df in tables:
        if df is not None and not df.empty:
            result["non_empty_tables"] += 1
            result["rows_total"] += int(df.shape[0])
            result["cols_total"] += int(df.shape[1])
            result["preview_shapes"].append(f"{df.shape[0]}x{df.shape[1]}")

    return result

# -----------------------------
# UI
# -----------------------------
st.title("⚽ Football AI V10 FIX")
st.caption("ສະບັບແກ້ພັງ + proxy + debug log + กันล้ม")

with st.sidebar:
    st.header("ຕັ້ງຄ່າ")
    url = st.text_input("ໃສ່ URL", value=DEFAULT_URL)

    mode = st.selectbox(
        "ວິທີດຶງ",
        options=["direct", "allorigins", "codetabs"],
        index=0,
    )

    timeout = st.slider("Timeout (วินาที)", min_value=5, max_value=60, value=DEFAULT_TIMEOUT)
    use_custom_proxy = st.checkbox("ໃຊ້ custom proxy ຈາກ Streamlit secrets", value=False)
    auto_find_links = st.checkbox("ຊອກຫາລິ້ງຄູ່ບານອັດຕະໂນມັດ", value=True)
    show_raw_html = st.checkbox("ສະແດງ HTML ບາງສ່ວນ", value=False)

run_btn = st.button("ດຶງຂໍ້ມູນ", type="primary", use_container_width=True)

if "last_logs" not in st.session_state:
    st.session_state["last_logs"] = []

if run_btn:
    try:
        with st.spinner("ກຳລັງດຶງຂໍ້ມູນ..."):
            html, meta = fetch_html(
                url=url,
                mode=mode,
                timeout=timeout,
                use_custom_proxy=use_custom_proxy,
            )

        logs = meta.get("logs", [])
        st.session_state["last_logs"] = logs

        st.subheader("ສະຖານະການດຶງຂໍ້ມູນ")
        c1, c2, c3 = st.columns(3)
        c1.metric("ສຳເລັດ", "ແມ່ນ" if meta.get("ok") else "ບໍ່")
        c2.metric("ວິທີທີ່ໃຊ້", meta.get("mode", "-"))
        c3.metric("Status", meta.get("status_code") if meta.get("status_code") is not None else "-")

        with st.expander("ເບິ່ງ log ການດຶງຂໍ້ມູນ", expanded=True):
            if logs:
                for line in logs:
                    st.code(line)
            else:
                st.write("ບໍ່ມີ log")

        if not html:
            st.error("❌ ດຶງຂໍ້ມູນບໍ່ໄດ້")
            st.info("ແນະນຳ: ລອງປ່ຽນວິທີດຶງເປັນ allorigins ຫຼື codetabs")
            st.stop()

        title = extract_title(html)
        visible_text = extract_visible_text(html)
        tables = parse_tables_from_html(html, logs)
        json_blocks = extract_json_blocks(html, logs)
        table_stats = analyze_tables(tables)

        st.subheader("ຜົນການອ່ານເບື້ອງຕົ້ນ")
        a1, a2, a3 = st.columns(3)
        a1.metric("ຈຳນວນ tables", table_stats["total_tables"])
        a2.metric("ຈຳນວນ JSON blocks", len(json_blocks))
        a3.metric("ຈຳນວນບັນທັດຈັບໄດ້", len(visible_text.split()))

        st.write("**Title:**", title if title else "-")
        st.write("**Final URL:**", meta.get("final_url", "-"))
        st.write("**Content-Type:**", meta.get("content_type", "-"))
        st.write("**ความยาวข้อความ:**", meta.get("content_length", 0))

        if auto_find_links:
            candidate_links = find_candidate_match_links(html, url, logs)
            with st.expander("ລິ້ງທີ່ຄາດວ່າເກີ່ຍວກັບຄູ່ບານ", expanded=False):
                if candidate_links:
                    for i, link in enumerate(candidate_links, start=1):
                        st.write(f"{i}. {link}")
                else:
                    st.write("ບໍ່ພົບລິ້ງຄູ່ບານຊັດເຈນ")

        st.subheader("ຂໍ້ຄວາມທີ່ອ່ານໄດ້")
        if visible_text:
            st.text_area("Visible text", visible_text, height=220)
        else:
            st.warning("ບໍ່ພົບຂໍ້ຄວາມທີ່ອ່ານໄດ້")

        st.subheader("ສະຫຼຸບ JSON")
        json_summary = summarize_json_blocks(json_blocks)
        if json_summary:
            st.dataframe(pd.DataFrame(json_summary), use_container_width=True)
        else:
            st.warning("ບໍ່ພົບ JSON block")

        st.subheader("ຕາຕະລາງທີ່ດຶງໄດ້")
        if tables:
            table_index = st.selectbox(
                "ເລືອກຕາຕະລາງ",
                options=list(range(len(tables))),
                format_func=lambda x: f"Table {x+1} | shape={tables[x].shape}",
            )
            st.dataframe(tables[table_index], use_container_width=True)
        else:
            st.warning("ບໍ່ມີ table ທີ່ອ່ານໄດ້")

        if show_raw_html:
            st.subheader("HTML ບາງສ່ວນ")
            st.code(html[:5000])

        with st.expander("Debug meta", expanded=False):
            st.json({
                "ok": meta.get("ok"),
                "status_code": meta.get("status_code"),
                "mode": meta.get("mode"),
                "final_url": meta.get("final_url"),
                "content_type": meta.get("content_type"),
                "content_length": meta.get("content_length"),
                "error": meta.get("error"),
                "table_stats": table_stats,
                "json_blocks": len(json_blocks),
            })

    except Exception as e:
        st.error(f"❌ App crash: {e}")
        st.exception(e)

else:
    st.info("ກົດ 'ດຶງຂໍ້ມູນ' ເພື່ອເລີ່ມ")
