import streamlit as st
import requests
import re

st.title("⚽ Goal7 XHR MODE (PRO)")

url = st.text_input(
    "ໃສ່ລິ້ງ",
    "https://goal7.co/priceball/?i=2799687"
)

def extract_id(url):
    match = re.search(r"i=(\d+)", url)
    return match.group(1) if match else None


if st.button("ດຶງລາຄາຈິງ (XHR)"):
    match_id = extract_id(url)

    if not match_id:
        st.error("ບໍ່ເຫັນ ID")
    else:
        try:
            # 🔥 API (goal7 ใช้)
            api_url = f"https://goal7.co/ajax/priceball?id={match_id}"

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": url
            }

            r = requests.get(api_url, headers=headers, timeout=15)

            st.success("ໂຫຼດ API ສຳເລັດ")

            data = r.text

            st.text_area("RAW DATA", data[:5000], height=400)

        except Exception as e:
            st.error(e)
