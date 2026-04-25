import streamlit as st
import requests

st.title("⚽ GOAL7 AUTO BOT")

try:
    url = "https://goal7.co/wp-admin/admin-ajax.php"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    data = {
        "action": "load_matches",
        "date": "2026-04-25"
    }

    res = requests.post(url, headers=headers, data=data, timeout=10)

    st.write("Status:", res.status_code)

    if res.status_code == 200:
        st.code(res.text[:1000])
    else:
        st.error("❌ โหลดไม่ได้")

except Exception as e:
    st.error(f"🔥 ERROR: {e}")
