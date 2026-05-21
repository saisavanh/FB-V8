import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="7M Live Score",
    layout="wide"
)

st.title("⚽ 7M Live Score")

html_code = """
<iframe
src="https://freelive.7mth.com/live.aspx?mark=th&TimeZone=%2B0700&wordAd=&wadurl=//&width=680&cpageBgColor=FFFFFF&tableFontSize=11&cborderColor=DDDDDD&ctdColor1=FFFFFF&ctdColor2=E0E9F6&clinkColor=0044DD&cdateFontColor=333333&cdateBgColor=FFFFFF&scoreFontSize=12&cteamFontColor=000000&cgoalFontColor=FF0000&cgoalBgColor=FFFFE1&cremarkFontColor=0000FF&cremarkBgColor=F7F8F3&Skins=10&teamWeight=400&scoreWeight=700&goalWeight=400&fontWeight=700&DSTbox="
height="900"
width="100%"
scrolling="yes"
frameborder="0">
</iframe>
"""

components.html(html_code, height=900)
