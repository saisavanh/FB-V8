import streamlit as st
import requests
from bs4 import BeautifulSoup

st.title("⚽ Goal7 SAFE MODE")

url = st.text_input(
    "ໃສ່ລິ້ງ",
    "https://goal7.co/priceball/?i=2799687"
)

if st.button("ດຶງຂໍ້ມູນ"):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)

        st.success("ໂຫຼດໄດ້")

        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n")

        st.text_area("Result", text[:5000], height=400)

    except Exception as e:
        st.error(e)
