import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("⚽ Goal7 REAL DATA MODE")

url = st.text_input(
    "Analyse URL",
    "https://goal7.co/analyse/?id=2799687"
)

if st.button("ດຶງຂໍ້ມູນຈິງ"):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)

        soup = BeautifulSoup(r.text, "html.parser")

        text = soup.get_text("\n")

        # filter เฉพาะ odds
        lines = []
        for line in text.split("\n"):
            if any(x in line for x in ["AH", "Over", "Under", "1X2", "สูง", "ต่ำ"]):
                lines.append(line.strip())

        st.success("ດຶງໄດ້ແລ້ວ")

        st.text_area("DATA", "\n".join(lines[:200]), height=400)

    except Exception as e:
        st.error(e)
