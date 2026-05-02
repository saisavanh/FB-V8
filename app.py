import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re
import time

st.set_page_config(
    page_title="Goal7 Scraper V1",
    layout="wide"
)

st.title("⚽ Goal7 Scraper + JS Reader V1")
st.caption("ດຶງຂໍ້ມູນ goal7 ໂດຍໃຊ້ requests + Playwright")

# =========================
# BASIC FETCH
# =========================
def fetch_requests(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text


# =========================
# PLAYWRIGHT FETCH
# =========================
def fetch_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )

        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        html = page.content()
        text = page.inner_text("body")

        browser.close()
        return html, text


# =========================
# PARSE TEXT
# =========================
def clean_lines(text):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line and line not in lines:
            lines.append(line)
    return lines


def extract_prices(lines):
    rows = []

    for line in lines:
        if any(x in line.lower() for x in ["ah", "1x2", "ou", "over", "under", "สูง", "ต่ำ"]):
            rows.append({
                "ປະເພດ": "price/text",
                "ຂໍ້ມູນ": line
            })

        if re.search(r"\d+\.\d+", line):
            rows.append({
                "ປະເພດ": "number/odds",
                "ຂໍ້ມູນ": line
            })

    return rows


# =========================
# UI
# =========================
url = st.text_input(
    "ໃສ່ລິ້ງ goal7",
    value="https://goal7.co/priceball/?i=2799687"
)

col1, col2 = st.columns(2)

with col1:
    run_req = st.button("ທົດສອບ requests")

with col2:
    run_js = st.button("ດຶງດ້ວຍ Playwright / JS")

if run_req:
    try:
        html = fetch_requests(url)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n")

        st.success("requests ດຶງໄດ້")
        st.text_area("HTML/Text", text[:10000], height=400)

    except Exception as e:
        st.error(f"requests error: {e}")


if run_js:
    try:
        html, text = fetch_playwright(url)

        st.success("Playwright ຮັນ JavaScript ສຳເລັດ")

        lines = clean_lines(text)
        price_rows = extract_prices(lines)

        tab1, tab2, tab3 = st.tabs(["ຂໍ້ມູນທີ່ອ່ານໄດ້", "ຕາຕະລາງລາຄາ", "HTML"])

        with tab1:
            st.text_area("Text from page", "\n".join(lines[:500]), height=500)

        with tab2:
            if price_rows:
                df = pd.DataFrame(price_rows)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("ຍັງບໍ່ພົບລາຄາຊັດເຈນ")

        with tab3:
            st.text_area("HTML after JS", html[:20000], height=500)

    except Exception as e:
        st.error("Playwright error")
        st.exception(e)
