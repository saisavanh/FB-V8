import re
import json
import math
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from typing import Any, Dict, List

st.set_page_config(page_title="V18 FULL SCRAPER", page_icon="⚽", layout="wide")

PAGE_URL = "https://goal7.co/%E0%B8%95%E0%B8%B2%E0%B8%A3%E0%B8%B2%E0%B8%87%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%A7%E0%B8%B1%E0%B8%99%E0%B8%99%E0%B8%B5%E0%B9%89/"
XHR_URL = "https://goal7.co/data/update2_backup_json.php"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/147.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Referer": "https://goal7.co/",
    "Accept-Language": "lo-LA,lo;q=0.9,th-TH;q=0.8,th;q=0.7,en-US;q=0.6,en;q=0.5",
    "Cache-Control": "no-cache",
}

def clean(x: Any) -> str:
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def to_num(x: Any, default: float = 0.0) -> float:
    try:
        s = clean(x).replace(",", "").replace("%", "")
        return float(s) if s else default
    except:
        return default

def fetch(url: str, cookie: str = "") -> Dict[str, Any]:
    headers = DEFAULT_HEADERS.copy()
    if cookie.strip():
        headers["Cookie"] = cookie.strip()

    try:
        r = requests.get(url, headers=headers, timeout=30)
        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "text": r.text,
            "headers": dict(r.headers),
            "error": "",
            "url": r.url,
        }
    except Exception as e:
        return {
            "ok": False,
            "status": 0,
            "text": "",
            "headers": {},
            "error": str(e),
            "url": url,
        }

def parse_html_tables(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    current_league = ""

    for tr in soup.find_all("tr"):
        text_all = clean(tr.get_text(" ", strip=True))

        if not text_all:
            continue

        ths = tr.find_all("th")
        tds = tr.find_all("td")

        if ths and len(text_all) > 4:
            current_league = text_all
            continue

        if len(tds) < 5:
            if any(k in text_all.lower() for k in ["premier", "bundesliga", "serie", "liga", "league", "cup"]):
                current_league = text_all
            continue

        cols = [clean(td.get_text(" ", strip=True)) for td in tds]

        # goal7 table ໂດຍທົ່ວໄປ: เวลา, ธง, สด, เจ้าบ้าน, ราคาบอล, ทีมเยือน, ครึ่งแรก, ผลบอล...
        item = {
            "ລີກ": current_league,
            "ເວລາ": cols[0] if len(cols) > 0 else "",
            "ສະຖານະ": cols[2] if len(cols) > 2 else "",
            "ເຈົ້າບ້ານ": cols[3] if len(cols) > 3 else "",
            "ລາຄາ": cols[4] if len(cols) > 4 else "",
            "ທີມຢາມ": cols[5] if len(cols) > 5 else "",
            "ຄຶ່ງແຮກ": cols[6] if len(cols) > 6 else "",
            "ຜົນບານ": cols[7] if len(cols) > 7 else "",
            "ວິເຄາະ": cols[8] if len(cols) > 8 else "",
            "raw": " | ".join(cols),
        }

        if item["ເຈົ້າບ້ານ"] or item["ທີມຢາມ"]:
            rows.append(item)

    return pd.DataFrame(rows)

def parse_xhr_json(raw: str) -> pd.DataFrame:
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return pd.DataFrame()

        max_len = max(len(x) for x in data if isinstance(x, list))
        cols = ["id", "home_score", "away_score", "s1", "s2", "s3", "s4", "s5", "time"]
        while len(cols) < max_len:
            cols.append(f"raw_{len(cols)}")

        fixed = [(x + [""] * max_len)[:max_len] for x in data if isinstance(x, list)]
        return pd.DataFrame(fixed, columns=cols[:max_len])
    except:
        return pd.DataFrame()

def poisson(lam: float, k: int) -> float:
    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def ai_pick(row: pd.Series) -> Dict[str, Any]:
    text_raw = clean(row.get("raw", "")) + " " + clean(row.get("ລາຄາ", ""))

    price_nums = re.findall(r"[-+]?\d+(?:\.\d+)?", text_raw)
    nums = [to_num(x) for x in price_nums]

    base_home = 50.0
    base_away = 50.0

    if nums:
        avg = sum(nums[:5]) / min(len(nums), 5)
        if avg < 0:
            base_home += 6
        elif avg > 0:
            base_away += 6

    home = clean(row.get("ເຈົ້າບ້ານ", ""))
    away = clean(row.get("ທີມຢາມ", ""))

    if home:
        base_home += 3
    if away:
        base_away += 2

    total = base_home + base_away
    hp = base_home / total * 100
    ap = base_away / total * 100

    if hp >= ap:
        side = "ເຈົ້າບ້ານ"
        conf = hp
    else:
        side = "ທີມຢາມ"
        conf = ap

    ou = "ສູງ" if len(text_raw) % 2 == 0 else "ຕ່ຳ"
    value = min(99, max(50, conf + (8 if nums else 0)))

    if value >= 75:
        level = "🔥 ຄູ່ເດັດ"
    elif value >= 65:
        level = "✅ ນ່າຫຼິ້ນ"
    else:
        level = "🟡 ລໍຖ້າ"

    return {
        "AI_ຝັ່ງ": side,
        "AI_%": round(conf, 2),
        "OU": ou,
        "Value_%": round(value, 2),
        "ລະດັບ": level,
    }

def add_ai(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()
    ai_rows = [ai_pick(row) for _, row in out.iterrows()]
    ai_df = pd.DataFrame(ai_rows)
    out = pd.concat([out.reset_index(drop=True), ai_df], axis=1)

    if "Value_%" in out.columns:
        out = out.sort_values(["Value_%", "AI_%"], ascending=False)

    return out

st.title("⚽ V18 FULL SCRAPER")
st.caption("ດຶງຊື່ທີມຈາກ HTML table + XHR สำรอง + AI วิเคราะห์")

cookie = st.text_area("ວາງ Cookie ຖ້າຕ້ອງການ", height=100)
show_debug = st.checkbox("ສະແດງ Debug", value=True)

if st.button("🚀 ດຶງຂໍ້ມູນ", use_container_width=True):
    page = fetch(PAGE_URL, cookie)

    c1, c2, c3 = st.columns(3)
    c1.metric("HTML Status", page["status"])
    c2.metric("Content-Type", page["headers"].get("content-type", "-"))
    c3.metric("Size", len(page["text"]))

    if not page["ok"]:
        st.error(page["error"] or page["text"][:500])
        st.stop()

    html_df = parse_html_tables(page["text"])
    final_df = add_ai(html_df)

    if not final_df.empty:
        st.success(f"ດຶງຕາຕະລາງໄດ້ {len(final_df)} ແຖວ")

        st.subheader("🔥 5 ຄູ່ເດັດ V18")
        st.dataframe(final_df.head(5), use_container_width=True)

        st.subheader("📊 ຕາຕະລາງທັງໝົດ")
        st.dataframe(final_df, use_container_width=True)

        csv = final_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ ດາວໂຫຼດ CSV",
            csv,
            "v18_goal7_full.csv",
            "text/csv",
            use_container_width=True
        )

    else:
        st.warning("HTML parse ບໍ່ເຫັນຕາຕະລາງ — ຈະລອງ XHR สำรอง")

        xhr = fetch(XHR_URL, cookie)
        st.write("XHR Status:", xhr["status"])

        xhr_df = parse_xhr_json(xhr["text"])
        if not xhr_df.empty:
            st.success(f"XHR ດຶງໄດ້ {len(xhr_df)} ແຖວ")
            st.dataframe(xhr_df, use_container_width=True)
        else:
            st.error("ດຶງບໍ່ສຳເລັດ")

    if show_debug:
        st.subheader("🧪 Debug HTML ຕົ້ນສະບັບ")
        st.write("Final URL:", page["url"])
        st.code(page["text"][:2500])
