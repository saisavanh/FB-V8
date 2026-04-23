import re
import json
import time
import random
from urllib.parse import quote

import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Football AI V10000", layout="wide")

# =========================
# CONFIG
# =========================
DEFAULT_URL = "https://goal7.co/"
TIMEOUT = 20

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    },
]

PROXY_MODES = {
    "direct": lambda url: url,
    "allorigins": lambda url: f"https://api.allorigins.win/raw?url={quote(url, safe='')}",
    "codetabs": lambda url: f"https://api.codetabs.com/v1/proxy?quest={quote(url, safe='')}",
    "thingproxy": lambda url: f"https://thingproxy.freeboard.io/fetch/{url}",
}

# =========================
# HELPERS
# =========================
def new_log():
    return []

def add_log(logs, msg):
    logs.append(msg)

def safe_text(x):
    if x is None:
        return ""
    return str(x).strip()

def pick_headers():
    return random.choice(HEADERS_LIST)

def normalize_spaces(text):
    return re.sub(r"\s+", " ", safe_text(text)).strip()

def looks_like_team_text(text):
    text = normalize_spaces(text)
    if len(text) < 3:
        return False
    bad = ["ผลบอล", "ตารางบอล", "Goal", "Copyright", "Privacy", "Login"]
    for b in bad:
        if b.lower() in text.lower():
            return False
    return True

# =========================
# FETCH
# =========================
def fetch_url(target_url, mode, logs):
    real_url = PROXY_MODES[mode](target_url)
    add_log(logs, f"เริ่มดึงข้อมูล: {target_url}")
    add_log(logs, f"โหมด: {mode}")
    add_log(logs, f"URL ที่เรียกจริง: {real_url}")

    try:
        r = requests.get(real_url, headers=pick_headers(), timeout=TIMEOUT)
        add_log(logs, f"Status: {r.status_code}")
        add_log(logs, f"Content-Type: {r.headers.get('Content-Type', '')}")
        add_log(logs, f"ความยาวข้อความ: {len(r.text)}")
        final_url = getattr(r, "url", real_url)
        add_log(logs, f"Final URL: {final_url}")

        title = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S)
        if m:
            title = normalize_spaces(m.group(1))
        add_log(logs, f"Title: {title if title else '-'}")

        return {
            "ok": r.status_code == 200 and len(r.text) > 0,
            "status": r.status_code,
            "html": r.text,
            "content_type": r.headers.get("Content-Type", ""),
            "final_url": final_url,
            "title": title,
        }
    except Exception as e:
        add_log(logs, f"ERROR: {e}")
        return {
            "ok": False,
            "status": 0,
            "html": "",
            "content_type": "",
            "final_url": "",
            "title": "",
        }

def fetch_with_fallback(target_url, preferred_mode, logs):
    order = [preferred_mode] + [m for m in PROXY_MODES.keys() if m != preferred_mode]
    tried = []

    for mode in order:
        tried.append(mode)
        result = fetch_url(target_url, mode, logs)
        if result["ok"] and ("html" in result["content_type"].lower() or "<html" in result["html"].lower()):
            result["mode"] = mode
            add_log(logs, f"สำเร็จด้วยโหมด: {mode}")
            return result

    add_log(logs, f"ดึงไม่สำเร็จทุกโหมด: {', '.join(tried)}")
    return {
        "ok": False,
        "status": 0,
        "html": "",
        "content_type": "",
        "final_url": "",
        "title": "",
        "mode": "none",
    }

# =========================
# PARSER TABLE
# =========================
def parse_html_tables(html, logs):
    try:
        tables = pd.read_html(html)
        add_log(logs, f"จำนวน tables: {len(tables)}")
        return tables
    except Exception as e:
        add_log(logs, f"อ่าน table ไม่ได้: {e}")
        return []

# =========================
# PARSER JSON BLOCK
# =========================
def extract_json_blocks(html, logs):
    blocks = re.findall(r"\{.*?\}", html, re.S)
    good = []

    for b in blocks[:500]:
        try:
            obj = json.loads(b)
            good.append(obj)
        except:
            pass

    add_log(logs, f"จำนวน JSON blocks: {len(good)}")
    return good

# =========================
# MATCH PARSER
# =========================
def detect_matches_from_text(html, logs):
    soup = BeautifulSoup(html, "html.parser")
    texts = []

    for tag in soup.find_all(["div", "span", "a", "td", "th", "li"]):
        tx = normalize_spaces(tag.get_text(" ", strip=True))
        if looks_like_team_text(tx):
            texts.append(tx)

    texts = list(dict.fromkeys(texts))

    rows = []
    pattern_vs = re.compile(r"(.+?)\s+(?:vs|v|-|พบ|เจอ)\s+(.+)", re.I)

    for t in texts:
        m = pattern_vs.match(t)
        if m:
            home = normalize_spaces(m.group(1))
            away = normalize_spaces(m.group(2))
            if home and away and home != away:
                rows.append({
                    "ลีก": "-",
                    "เจ้าบ้าน": home,
                    "ทีมเยือน": away,
                    "1": "",
                    "X": "",
                    "2": "",
                    "AH": "",
                    "O/U": "",
                })

    add_log(logs, f"จำนวนคู่ที่จับได้: {len(rows)}")
    return rows

# =========================
# TABLE CLASSIFY
# =========================
def classify_tables(tables):
    one_x_two = []
    ah = []
    ou = []
    other = []

    for df in tables:
        cols = " | ".join([str(c) for c in df.columns]).lower()
        all_text = cols + " " + " ".join(df.astype(str).fillna("").head(5).to_string().lower().split())

        if "1" in cols and "x" in cols and "2" in cols:
            one_x_two.append(df)
        elif "ah" in all_text or "handicap" in all_text:
            ah.append(df)
        elif "o/u" in all_text or "over" in all_text or "under" in all_text:
            ou.append(df)
        else:
            other.append(df)

    return one_x_two, ah, ou, other

# =========================
# ANALYSIS
# =========================
def analyze_match_rows(rows):
    result = []
    for r in rows:
        home = safe_text(r.get("เจ้าบ้าน"))
        away = safe_text(r.get("ทีมเยือน"))

        score = 0
        note = []

        if home and away:
            score += 1
            note.append("จับชื่อคู่ได้")

        if safe_text(r.get("AH")):
            score += 1
            note.append("มี AH")

        if safe_text(r.get("O/U")):
            score += 1
            note.append("มี O/U")

        if safe_text(r.get("1")) and safe_text(r.get("X")) and safe_text(r.get("2")):
            score += 1
            note.append("มี 1X2")

        if score >= 3:
            level = "สูง"
        elif score == 2:
            level = "กลาง"
        else:
            level = "ต้น"

        result.append({
            "คู่": f"{home} vs {away}",
            "ระดับข้อมูล": level,
            "หมายเหตุ": ", ".join(note) if note else "-",
        })
    return pd.DataFrame(result)

# =========================
# UI
# =========================
st.title("⚽ Football AI V10000")
st.caption("parser จริง + proxy + debug log + กันพัง + แยกตาราง + วิเคราะห์เบื้องต้น")

col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("ใส่ URL", value=DEFAULT_URL)
with col2:
    mode = st.selectbox("เลือกโหมด", list(PROXY_MODES.keys()), index=0)

run = st.button("ดึงข้อมูล", use_container_width=True)

if run:
    logs = new_log()

    with st.spinner("กำลังดึงข้อมูล..."):
        result = fetch_with_fallback(url, mode, logs)

        st.subheader("ສະຖານະການດຶງຂໍ້ມູນ")
        st.write("สำเร็จ" if result["ok"] else "ล้มเหลว")
        st.write("วิธีที่ใช้:", result.get("mode", "-"))
        st.write("Status:", result["status"])

        with st.expander("ເບິ່ງ log ການດຶງຂໍ້ມູນ", expanded=True):
            for x in logs:
                st.code(x, language="text")

        if not result["ok"]:
            st.error("ดึงข้อมูลไม่สำเร็จ")
        else:
            html = result["html"]

            st.subheader("ຜົນການອ່ານເບື້ອງຕົ້ນ")
            tables = parse_html_tables(html, logs)
            json_blocks = extract_json_blocks(html, logs)
            match_rows = detect_matches_from_text(html, logs)

            c1, c2, c3 = st.columns(3)
            c1.metric("จำนวน tables", len(tables))
            c2.metric("จำนวน JSON blocks", len(json_blocks))
            c3.metric("จำนวนบังเกิดคู่จับได้", len(match_rows))

            st.write(f"**Title:** {result['title'] or '-'}")
            st.write(f"**Final URL:** {result['final_url'] or '-'}")
            st.write(f"**Content-Type:** {result['content_type'] or '-'}")
            st.write(f"**ความยาวข้อความ:** {len(html)}")

            one_x_two, ah, ou, other = classify_tables(tables)

            st.subheader("1X2")
            if one_x_two:
                for i, df in enumerate(one_x_two[:3], 1):
                    st.write(f"ตาราง 1X2 #{i}")
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("ไม่พบตาราง 1X2 ชัดเจน")

            st.subheader("AH")
            if ah:
                for i, df in enumerate(ah[:3], 1):
                    st.write(f"ตาราง AH #{i}")
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("ไม่พบตาราง AH ชัดเจน")

            st.subheader("O/U")
            if ou:
                for i, df in enumerate(ou[:3], 1):
                    st.write(f"ตาราง O/U #{i}")
                    st.dataframe(df, use_container_width=True)
            else:
                st.info("ไม่พบตาราง O/U ชัดเจน")

            st.subheader("คู่บอลที่จับได้")
            if match_rows:
                match_df = pd.DataFrame(match_rows)
                st.dataframe(match_df, use_container_width=True)

                st.subheader("วิเคราะห์เบื้องต้น")
                ana_df = analyze_match_rows(match_rows)
                st.dataframe(ana_df, use_container_width=True)
            else:
                st.warning("ยังจับคู่บอลไม่ชัด อาจต้องใช้ endpoint จริงจาก network")

            st.subheader("ตารางอื่น ๆ")
            if other:
                for i, df in enumerate(other[:5], 1):
                    st.write(f"ตารางอื่น #{i}")
                    st.dataframe(df, use_container_width=True)

            with st.expander("HTML ตัวอย่าง 3000 ตัวอักษรแรก"):
                st.code(html[:3000], language="html")
