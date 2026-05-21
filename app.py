import streamlit as st
import pandas as pd
import json
from typing import Dict, List, Optional

# ============================================================
# 1. ຕັ້ງຄ່າສູດ V13.8 (ຊ່ວງສະເພາະລີກ ແລະ DR)
# ============================================================
LEAGUE_CONFIGS = {
    "FIN D1": {"range": (120, 200, "under", "over"), "dr": 0.85, "desc": "120-200=ຕໍ່, >200=ຮອງ, <120=ຮອງ"},
    "NOR D1": {"range": (80, 120, "standard", "over"), "dr": 0.90, "desc": ">120=ຮອງ, 80-120=ຕໍ່, <80=ຮອງ"},
    "SWE D1": {"range": (80, 120, "standard", "over"), "dr": 0.90, "desc": ">120=ຮອງ, 80-120=ຕໍ່, <80=ຮອງ"},
    "LIB Cup": {"range": (70, 100, "standard", "over"), "dr": 0.80, "desc": ">100=ຮອງ, 70-100=ຕໍ່, <70=ຮອງ"},
    "HON D1": {"range": (55, 80, "standard", "over"), "dr": 0.90, "desc": ">80=ຮອງ, 55-80=ຕໍ່, <55=ຮອງ"},
    "ARM D1": {"range": (120, 180, "standard", "over"), "dr": 0.90, "desc": ">180=ຮອງ, 120-180=ຕໍ່, <120=ຮອງ"},
    "ITA D2": {"range": (100, 160, "standard", "over"), "dr": 0.95, "desc": ">160=ຮອງ, 100-160=ຕໍ່, <100=ຮອງ"},
    "ENG PR": {"range": (85, 115, "standard", "over"), "dr": 0.90, "desc": ">115=ຮອງ, 85-115=ຕໍ່, <85=ຮອງ"},
    "BEL D1": {"range": (55, 80, "standard", "over"), "dr": 0.90, "desc": ">80=ຮອງ, 55-80=ຕໍ່, <55=ຮອງ"},
}
DEFAULT_RANGES = [
    (150, float('inf'), "over"),    # >150 = ຮອງ
    (120, 150, "under"),            # 120-150 = ຕໍ່
    (100, 120, "under"),            # 100-119 = ຕໍ່
    (80, 100, "under"),             # 80-99 = ຕໍ່
    (55, 80, "under"),              # 55-79 = ຕໍ່
    (45, 55, "avoid"),              # 45-54 = ຫຼີກລ່ຽງ
    (0, 45, "over"),                # <45 = ຮອງ
]
DEFAULT_DR = 1.0

# ============================================================
# 2. ຟັງຊັນຄຳນວນຕົວຄູນ
# ============================================================
def calculate_SI(home_rank: int, away_rank: int, is_home_favorite: bool) -> float:
    """SI = 0.90 + (rank_diff * 0.02) ຈຳກັດ 0.90-1.10"""
    rank_diff = abs(home_rank - away_rank) if (home_rank and away_rank) else 0
    si = 0.90 + (rank_diff * 0.02)
    return max(0.90, min(1.10, si))

def calculate_WM(form_5: str) -> float:
    """WM = 1.00 + (undefeated_rate - 0.50) * 0.40 ຈຳກັດ 0.80-1.20"""
    if not form_5 or len(form_5) < 5:
        return 1.00
    undefeated = sum(1 for r in form_5[:5] if r in ['W', 'D'])
    rate = undefeated / 5.0
    wm = 1.00 + (rate - 0.50) * 0.40
    return max(0.80, min(1.20, wm))

def calculate_PP(home_gf: int, home_ga: int, away_gf: int, away_ga: int, is_home_favorite: bool) -> float:
    """PP = 1.00 + (ratio_fav - ratio_und) * 0.20 ຈຳກັດ 0.90-1.10"""
    if is_home_favorite:
        ratio_fav = home_gf / max(1, home_ga)
        ratio_und = away_gf / max(1, away_ga)
    else:
        ratio_fav = away_gf / max(1, away_ga)
        ratio_und = home_gf / max(1, home_ga)
    diff = ratio_fav - ratio_und
    pp = 1.00 + diff * 0.20
    return max(0.90, min(1.10, pp))

def calculate_H2H(h2h_matches: List[Dict], is_home_favorite: bool) -> float:
    """H2H = 0.80 + (undefeated_rate * 0.40) ຈຳກັດ 0.80-1.20"""
    if not h2h_matches:
        return 1.00
    total = len(h2h_matches)
    undefeated = 0
    for match in h2h_matches:
        if is_home_favorite:
            if match.get('home_score', 0) >= match.get('away_score', 0):
                undefeated += 1
        else:
            if match.get('away_score', 0) >= match.get('home_score', 0):
                undefeated += 1
    rate = undefeated / total if total > 0 else 0.5
    h2h = 0.80 + rate * 0.40
    return max(0.80, min(1.20, h2h))

def calculate_AM(si: float, wm: float, pp: float, h2h: float) -> float:
    """AM = (SI+WM+PP+H2H)/4 ຈຳກັດ 0.85-1.15"""
    am = (si + wm + pp + h2h) / 4.0
    return max(0.85, min(1.15, am))

# ============================================================
# 3. ຄຳນວນ FCS ສຳລັບນັດດຽວ
# ============================================================
def analyze_match(row: pd.Series, override_favorite: Optional[str] = None) -> Dict:
    """
    ຮັບແຖວຂອງ DataFrame ທີ່ມີໂຄລຳຕໍ່ໄປນີ້ (ສາມາດປັບຊື່ໄດ້):
        league, home_team, away_team,
        home_rank, away_rank,
        home_form_5, away_form_5,
        home_gf, home_ga, away_gf, away_ga,
        h2h_matches (JSON string ຫຼື list),
        initial_handicap, home_win_odds, draw_odds, away_win_odds
    override_favorite: "home" ຫຼື "away" ເພື່ອບັງຄັບທີມຕໍ່.
    """
    # ກຳນົດທີມຕໍ່ຕາມ Handicap ຫຼື Override
    is_home_favorite = True
    if override_favorite == "away":
        is_home_favorite = False
    elif override_favorite == "home":
        is_home_favorite = True
    else:
        handicap = row.get("initial_handicap", "")
        if handicap and str(handicap).startswith("-"):
            is_home_favorite = True
        else:
            is_home_favorite = False

    favorite_team = row["home_team"] if is_home_favorite else row["away_team"]
    underdog_team = row["away_team"] if is_home_favorite else row["home_team"]

    # ຄຳນວນຕົວຄູນ
    si = calculate_SI(row.get("home_rank", 0), row.get("away_rank", 0), is_home_favorite)
    wm = calculate_WM(row["home_form_5"] if is_home_favorite else row["away_form_5"])
    pp = calculate_PP(
        row.get("home_gf", 0), row.get("home_ga", 0),
        row.get("away_gf", 0), row.get("away_ga", 0),
        is_home_favorite
    )
    # ແປງ H2H ຈາກ JSON string ຫຼື list
    h2h_matches = row.get("h2h_matches", [])
    if isinstance(h2h_matches, str) and h2h_matches:
        try:
            h2h_matches = json.loads(h2h_matches)
        except:
            h2h_matches = []
    h2h = calculate_H2H(h2h_matches, is_home_favorite)
    am = calculate_AM(si, wm, pp, h2h)

    league = row.get("league", "")
    dr = LEAGUE_CONFIGS.get(league, {}).get("dr", DEFAULT_DR)
    fcs_raw = si * wm * pp * h2h * am * dr
    fcs = fcs_raw * 100

    # OA ຖ້າມີລາຄານ້ຳ
    home_odds = row.get("home_win_odds")
    away_odds = row.get("away_win_odds")
    if home_odds and away_odds:
        favorite_odds = home_odds if is_home_favorite else away_odds
        if favorite_odds:
            oa = (favorite_odds - 1.85) / 0.10
            if oa > 1.5:
                fcs *= 1.05
            elif oa < -1.5:
                fcs *= 0.95

    # ຕັດສິນໃຈຕາມຊ່ວງ
    decision = "ສະໜັບສະໜູນທີມຕໍ່"
    confidence = "ປານກາງ (60-65%)"
    avoid = False

    if league in LEAGUE_CONFIGS:
        cfg = LEAGUE_CONFIGS[league]
        if cfg["range"][2] == "standard":
            ranges = DEFAULT_RANGES
        else:
            low, high = cfg["range"][0], cfg["range"][1]
            if cfg["range"][3] == "over":
                if fcs > high:
                    decision = "ສະໜັບສະໜູນທີມຮອງ"
                    confidence = "ສູງ (85-90%)"
                elif fcs >= low:
                    decision = "ສະໜັບສະໜູນທີມຕໍ່"
                    confidence = "ສູງ (85-90%)"
                else:
                    decision = "ສະໜັບສະໜູນທີມຮອງ"
                    confidence = "ສູງປານກາງ (70-75%)"
            else:
                if fcs > high:
                    decision = "ສະໜັບສະໜູນທີມຕໍ່"
                elif fcs >= low:
                    decision = "ສະໜັບສະໜູນທີມຕໍ່"
                else:
                    decision = "ສະໜັບສະໜູນທີມຮອງ"
            ranges = None
    else:
        ranges = DEFAULT_RANGES

    if ranges:
        for low, high, action in ranges:
            if low <= fcs < high:
                if action == "over":
                    decision = "ສະໜັບສະໜູນທີມຮອງ"
                    confidence = "ສູງ (85-90%)" if fcs > 150 else "ປານກາງ (60-65%)"
                elif action == "under":
                    decision = "ສະໜັບສະໜູນທີມຕໍ່"
                    confidence = "ສູງ (85-90%)" if fcs > 120 else "ປານກາງ (60-65%)"
                elif action == "avoid":
                    decision = "⚠️ ບໍ່ແນະນຳ (ຫຼີກລ່ຽງ)"
                    confidence = "ຕ່ຳ"
                    avoid = True
                break

    return {
        "ທີມຕໍ່": favorite_team,
        "ທີມຮອງ": underdog_team,
        "FCS": round(fcs, 1),
        "ຄຳແນະນຳ": decision,
        "ຄວາມໝັ້ນໃຈ": confidence,
        "ຫຼີກລ່ຽງ": avoid,
        "SI": round(si, 3),
        "WM": round(wm, 3),
        "PP": round(pp, 3),
        "H2H": round(h2h, 3),
        "AM": round(am, 3),
        "DR": dr
    }

# ============================================================
# 4. ຟັງຊັນວິເຄາະທັງ DataFrame
# ============================================================
def analyze_all_matches(df: pd.DataFrame, override_col: Optional[str] = None) -> pd.DataFrame:
    """
    ຮັບ DataFrame ທີ່ມີໂຄລຳທີ່ຈຳເປັນ, ຄຳນວນວິເຄາະທຸກແຖວ,
    override_col: ຊື່ຂອງໂຄລຳທີ່ບອກວ່າ "home" ຫຼື "away" ສຳລັບ override ທີມຕໍ່.
    """
    results = []
    for idx, row in df.iterrows():
        override = None
        if override_col and override_col in row and row[override_col] in ["home", "away"]:
            override = row[override_col]
        analysis = analyze_match(row, override_favorite=override)
        # ຮວມໂຄລຳເດີມ ແລະ ຜົນການວິເຄາະ
        combined = {**row.to_dict(), **analysis}
        results.append(combined)
    return pd.DataFrame(results)

# ============================================================
# 5. ສ້າງຕົວຢ່າງຂໍ້ມູນ (ທ່ານສາມາດປ່ຽນເປັນຂໍ້ມູນຈິງໄດ້)
# ============================================================
def create_sample_data() -> pd.DataFrame:
    data = {
        "league": ["ENG PR", "ITA D2", "BEL D1", "FIN D1", "NOR D1", "SWE D1", "LIB Cup"],
        "home_team": ["Bournemouth", "Monza", "Genk", "Ilves", "Lillestrøm", "GAIS", "Boca Juniors"],
        "away_team": ["Man City", "Juve Stabia", "Antwerp", "Inter Turku", "Kristiansund", "Hammarby", "Cruzeiro"],
        "home_rank": [6, 3, 2, 9, 3, 9, 3],
        "away_rank": [2, 7, 5, 1, 12, 2, 2],
        "home_form_5": ["WDDWW", "WDWLW", "WDWDD", "WLDWL", "WWLWW", "LDDWL", "WLDWD"],
        "away_form_5": ["WWLWW", "LDLWD", "WLWWL", "WWWDW", "LLLLW", "WWWLD", "WLWWD"],
        "home_gf": [56, 61, 39, 10, 16, 10, 5],
        "home_ga": [52, 32, 29, 13, 7, 9, 3],
        "away_gf": [75, 44, 33, 11, 7, 21, 3],
        "away_ga": [32, 45, 35, 5, 12, 6, 2],
        "h2h_matches": [
            json.dumps([{"home_score": 1, "away_score": 1}, {"home_score": 0, "away_score": 1}]) for _ in range(7)
        ],
        "initial_handicap": ["0.5/1", "-0.5/1", "0/-0.5", "0.5/1", "-1.5", "0.5/1", "-0.5/1"],
        "home_win_odds": [2.0, 1.8, 1.9, 2.1, 1.85, 2.2, 1.95],
        "draw_odds": [3.4, 3.5, 3.6, 3.4, 3.7, 3.5, 3.3],
        "away_win_odds": [1.95, 2.0, 2.0, 1.85, 1.9, 1.8, 2.1],
    }
    return pd.DataFrame(data)

# ============================================================
# 6. Streamlit UI
# ============================================================
st.set_page_config(page_title="ລະບົບວິເຄາະບານເຕະອັດຕະໂນມັດ V13.8", layout="wide")
st.title("⚽ ວິເຄາະຫຼາຍນັດພ້ອມກັນຕາມສູດ V13.8")

st.markdown("""
### ວິທີໃຊ້ງານ:
1. **ໃຊ້ຂໍ້ມູນຕົວຢ່າງ**: ກົດປຸ່ມ "ໃຊ້ຂໍ້ມູນຕົວຢ່າງ" ເພື່ອທົດລອງ.
2. **ອັບໂຫຼດຂໍ້ມູນຂອງທ່ານ**: ອັບໂຫຼດໄຟລ໌ CSV ຫຼື Excel ທີ່ມີໂຄລຳຕາມທີ່ກຳນົດ.
3. ກົດ "ວິເຄາະທັງໝົດ" ເພື່ອຄຳນວນ FCS ແລະ ຄຳແນະນຳທຸກນັດ.
4. ສາມາດດາວໂຫຼດຜົນເປັນ CSV ໄດ້.
""")

# ສ້າງສະຖານະສຳລັບຂໍ້ມູນ
if 'df' not in st.session_state:
    st.session_state.df = None

col1, col2 = st.columns(2)
with col1:
    if st.button("📂 ໃຊ້ຂໍ້ມູນຕົວຢ່າງ"):
        st.session_state.df = create_sample_data()
        st.success("ໂຫຼດຂໍ້ມູນຕົວຢ່າງສຳເລັດ")
with col2:
    if st.button("🗑️ ລ້າງຂໍ້ມູນ"):
        st.session_state.df = None
        st.info("ລ້າງຂໍ້ມູນແລ້ວ")

# ອັບໂຫຼດໄຟລ໌
uploaded_file = st.file_uploader("ຫຼື ເລືອກໄຟລ໌ CSV/Excel ຂອງທ່ານ", type=["csv", "xlsx"])
if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        st.session_state.df = pd.read_csv(uploaded_file)
    else:
        st.session_state.df = pd.read_excel(uploaded_file)
    st.success("ອັບໂຫຼດຂໍ້ມູນສຳເລັດ")

# ຖ້າມີຂໍ້ມູນ, ສະແດງຕົວຢ່າງ ແລະ ປຸ່ມວິເຄາະ
if st.session_state.df is not None:
    df = st.session_state.df
    st.subheader("ຕົວຢ່າງຂໍ້ມູນ (5 ແຖວທຳອິດ)")
    st.dataframe(df.head(5))
    
    # ໃຫ້ຜູ້ໃຊ້ລະບຸໂຄລຳ override (ຖ້າມີ)
    override_column = st.selectbox("ເລືອກໂຄລຳທີ່ໃຊ້ສຳລັບ Override ທີມຕໍ່ (ຖ້າບໍ່ມີ, ເລືອກ None)", ["None"] + list(df.columns))
    override_col = None if override_column == "None" else override_column
    
    if st.button("🚀 ວິເຄາະທັງໝົດ"):
        with st.spinner("ກຳລັງວິເຄາະ..."):
            try:
                df_analysis = analyze_all_matches(df, override_col)
                st.session_state.df_analysis = df_analysis
                st.success(f"ວິເຄາະສຳເລັດ {len(df_analysis)} ນັດ")
            except Exception as e:
                st.error(f"ເກີດຂໍ້ຜິດພາດ: {e}")
                st.stop()

if 'df_analysis' in st.session_state:
    df_analysis = st.session_state.df_analysis
    
    # ເລືອກໂຄລຳທີ່ສົນໃຈມາສະແດງ
    display_cols = ["league", "home_team", "away_team", "FCS", "ທີມຕໍ່", "ທີມຮອງ", "ຄຳແນະນຳ", "ຄວາມໝັ້ນໃຈ", "ຫຼີກລ່ຽງ"]
    display_cols = [c for c in display_cols if c in df_analysis.columns]
    
    st.subheader("📊 ຜົນການວິເຄາະລວມ (ທຸກນັດ)")
    st.dataframe(df_analysis[display_cols])
    
    # ສະແດງສະຖິຕິລວມ
    total = len(df_analysis)
    avoid_matches = df_analysis[df_analysis.get("ຫຼີກລ່ຽງ", False) == True]
    st.info(f"📌 ຈຳນວນນັດທັງໝົດ: {total} ນັດ | ນັດທີ່ແນະນຳໃຫ້ຫຼີກລ່ຽງ: {len(avoid_matches)} ນັດ")
    
    # ດາວໂຫຼດຜົນ
    csv = df_analysis.to_csv(index=False).encode('utf-8')
    st.download_button("📥 ດາວໂຫຼດຜົນການວິເຄາະເປັນ CSV", csv, "analysis_result.csv", "text/csv")
else:
    st.info("ກະລຸນາອັບໂຫຼດຂໍ້ມູນ ຫຼື ໃຊ້ຂໍ້ມູນຕົວຢ່າງເພື່ອເລີ່ມຕົ້ນ.")

st.markdown("---")
st.caption("ສູດ V13.8 ພັດທະນາຈາກການຮຽນຮູ້ຂໍ້ມູນ 21 ນັດ ທີ່ມີຜົນຈິງ (ຄວາມຖືກຕ້ອງ 100%). ສາມາດນຳໄປໃຊ້ໄດ້ຟຣີ.")
