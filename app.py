# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from scraper import fetch_live_matches
from analyzer import basic_stats, team_stats

st.set_page_config(page_title="7m Football Analyzer", layout="wide")
st.title("⚽ ວິເຄາະການແຂ່ງຂັນຟຸດບອລສົດຈາກ 7m")

# Sidebar ສຳລັບຕົວເລືອກ
with st.sidebar:
    st.header("ຕົວເລືອກການກັ່ນຕອງ")
    lang = st.selectbox("ພາສາ", options=["th", "en", "cn"], index=0, format_func=lambda x: {"th":"ไทย", "en":"English", "cn":"中文"}[x])
    width = st.number_input("ຄວາມກວ້າງ (px)", value=700, step=10)
    if st.button("🔄 ດຶງຂໍ້ມູນລ່າສຸດ"):
        with st.spinner("ກຳລັງດຶງຂໍ້ມູນ..."):
            df_raw = fetch_live_matches(mark=lang, width=width)
            st.session_state["df"] = df_raw
            st.session_state["filtered_df"] = df_raw
        st.success("ດຶງຂໍ້ມູນສຳເລັດ!")

# ການເລືອກລີກ ແລະ ທີມ
if "df" in st.session_state and not st.session_state["df"].empty:
    df = st.session_state["df"]
    
    col1, col2 = st.columns(2)
    with col1:
        leagues = ["ທັງໝົດ"] + sorted(df["league"].unique().tolist())
        selected_league = st.selectbox("ເລືອກລີກ", leagues)
    with col2:
        teams = ["ທັງໝົດ"] + sorted(pd.concat([df["home_team"], df["away_team"]]).unique().tolist())
        selected_team = st.selectbox("ເລືອກທີມ", teams)
    
    # ກັ່ນຕອງຂໍ້ມູນ
    filtered_df = df.copy()
    if selected_league != "ທັງໝົດ":
        filtered_df = filtered_df[filtered_df["league"] == selected_league]
    if selected_team != "ທັງໝົດ":
        filtered_df = filtered_df[(filtered_df["home_team"] == selected_team) | (filtered_df["away_team"] == selected_team)]
    st.session_state["filtered_df"] = filtered_df
    
    # ສະແດງຕາຕະລາງ
    st.subheader("📋 ລາຍການແຂ່ງຂັນ")
    st.dataframe(filtered_df, use_container_width=True)
    
    # ສະຖິຕິລວມ
    stats = basic_stats(filtered_df)
    if stats:
        st.subheader("📊 ສະຖິຕິລວມ")
        col_a, col_b, col_c, col_d, col_e = st.columns(5)
        col_a.metric("ນັດທັງໝົດ", stats["total_matches"])
        col_b.metric("ປະຕູທັງໝົດ", stats["total_goals"])
        col_c.metric("ຄ່າສະເລ່ຍປະຕູ/ນັດ", stats["avg_goals_per_match"])
        col_d.metric("ເຈົ້າບ້ານຊະນະ", stats["home_wins"])
        col_e.metric("ທີມເຢັນຊະນະ", stats["away_wins"])
    
    # ສະຖິຕິສະເພາະທີມ (ຖ້າເລືອກ)
    if selected_team != "ທັງໝົດ":
        team_stat = team_stats(filtered_df, selected_team)
        if team_stat:
            st.subheader(f"📈 ສະຖິຕິຂອງ {selected_team}")
            col_f, col_g, col_h, col_i = st.columns(4)
            col_f.metric("ແຂ່ງຂັນ", team_stat["matches"])
            col_g.metric("ຍິງໄດ້", team_stat["goals_for"])
            col_h.metric("ເສຍ", team_stat["goals_against"])
            col_i.metric("ຜົນຕ່າງປະຕູ", team_stat["goal_diff"])
    
    # ກຣາຟສະແດງປະຕູຕໍ່ນັດ
    st.subheader("📉 ກຣາຟສະຖິຕິປະຕູ")
    filtered_df[["home_goals", "away_goals"]] = filtered_df["score"].apply(lambda x: pd.Series(parse_score(x)))
    goals_melted = filtered_df.melt(id_vars=["home_team", "away_team"], value_vars=["home_goals", "away_goals"], var_name="team_type", value_name="goals")
    fig = px.bar(goals_melted, x="home_team", y="goals", color="team_type", barmode="group", title="ປະຕູເຈົ້າບ້ານ ແລະ ທີມເຢັນຕໍ່ນັດ")
    st.plotly_chart(fig, use_container_width=True)
    
    # ຟີດເຈີຄາດເດົາຜົນ (ງ່າຍໆ)
    if selected_team != "ທັງໝົດ" and len(filtered_df) > 3:
        st.subheader("🔮 ການຄາດເດົາແນວໂນ້ມຜົນການແຂ່ງຂັນ")
        avg_for = team_stat["avg_goals_for"]
        avg_against = team_stat["avg_goals_against"]
        if avg_for > avg_against:
            st.success(f"ທີມ {selected_team} ມີແນວໂນ້ມຍິງຫຼາຍກວ່າເສຍ (ສະເລ່ຍ {avg_for} ປະຕູຕໍ່ນັດ, ເສຍ {avg_against}) ຈຶ່ງມີໂອກາດຊະນະສູງ.")
        else:
            st.warning(f"ທີມ {selected_team} ມີສະຖິຕິເສຍຫຼາຍກວ່າຍິງ (ສະເລ່ຍ {avg_for} ປະຕູຕໍ່ນັດ, ເສຍ {avg_against}) ຈົ່ງລະວັງ!")
else:
    st.info("ກົດປຸ່ມ 'ດຶງຂໍ້ມູນລ່າສຸດ' ທາງຊ້າຍເພື່ອເລີ່ມຕົ້ນ.")
