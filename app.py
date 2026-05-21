# app.py
import streamlit as st

st.set_page_config(page_title="7m Live Scores", layout="wide")
st.title("⚽ ຕາຕະລາງຄະແນນສົດ ຈາກ 7m")

# ສ້າງ sidebar ໃຫ້ຜູ້ໃຊ້ປັບຄ່າຕ່າງໆ
with st.sidebar:
    st.header("ປັບແຕ່ງວິດເຈັດ")
    lang = st.selectbox("ພາສາ", options=["th", "en", "cn"], index=0, format_func=lambda x: {"th":"ไทย", "en":"English", "cn":"中文"}[x])
    width = st.number_input("ຄວາມກວ້າງ (px)", value=700, step=10)
    team_color = st.color_picker("ສີຊື່ທີມ", "#000000")
    score_color = st.color_picker("ສີຄະແນນ", "#FF0000")
    row_color1 = st.color_picker("ສີແຖວຄູ່", "#FFFFFF")
    row_color2 = st.color_picker("ສີແຖວຄີກ", "#E0E9F6")

# ສ້າງ HTML ທີ່ບັນຈຸ JavaScript ດຽວກັບຕົ້ນສະບັບ
# ແຕ່ປ່ຽນຄ່າຕາມທີ່ຜູ້ໃຊ້ເລືອກ
html_code = f"""
<script>
    var timeZone = '%2B0700';
    var dstbox = '';
    var cpageBgColor = 'FFFFFF';
    var wordAd = '';
    var wadurl = '//';
    var width = '{width}';
    var tableFontSize = '11';
    var cborderColor = 'DDDDDD';
    var ctdColor1 = '{row_color1.lstrip("#")}';
    var ctdColor2 = '{row_color2.lstrip("#")}';
    var clinkColor = '0044DD';
    var cdateFontColor = '333333';
    var cdateBgColor = 'FFFFFF';
    var scoreFontSize = '12';
    var cteamFontColor = '{team_color.lstrip("#")}';
    var cgoalFontColor = '{score_color.lstrip("#")}';
    var cgoalBgColor = 'FFFFE1';
    var cremarkFontColor = '0000FF';
    var mark = '{lang}';
    var cremarkBgColor = 'F7F8F3';
    var Skins = '10';
    var teamWeight = '400';
    var scoreWeight = '700';
    var goalWeight = '400';
    var fontWeight = '700';

    document.write("<iframe src='//freelive.7mth2.com/live.aspx?mark="+ mark +"&TimeZone=" + timeZone + "&wordAd=" + wordAd + "&cpageBgColor="+ cpageBgColor +"&wadurl=" + wadurl + "&width=" + width + "&tableFontSize=" + tableFontSize + "&cborderColor=" + cborderColor + "&ctdColor1=" + ctdColor1 + "&ctdColor2=" + ctdColor2 + "&clinkColor=" + clinkColor + "&cdateFontColor="+ cdateFontColor +"&cdateBgColor=" + cdateBgColor + "&scoreFontSize=" + scoreFontSize + "&cteamFontColor=" + cteamFontColor + "&cgoalFontColor=" + cgoalFontColor + "&cgoalBgColor=" + cgoalBgColor + "&cremarkFontColor=" + cremarkFontColor + "&cremarkBgColor=" + cremarkBgColor + "&Skins=" + Skins + "&teamWeight=" + teamWeight + "&scoreWeight=" + scoreWeight + "&goalWeight=" + goalWeight +"&fontWeight="+ fontWeight +"&DSTbox="+ dstbox +"'  height='100%' width='{width}' scrolling='yes' border='0' frameborder='0'></iframe>");
</script>
"""

# ແຊກ HTML ເຂົ້າໄປໃນ Streamlit
st.components.v1.html(html_code, height=800, scrolling=True)

st.caption("📌 ຂໍ້ມູນສະໂກດສົດຈາກ 7m (freelive.7mth2.com) — ສາມາດປັບສີ ແລະ ພາສາໄດ້ທາງເບື້ອງຊ້າຍ")
