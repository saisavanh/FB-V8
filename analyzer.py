# analyzer.py
import pandas as pd
import numpy as np

def parse_score(score_str):
    """
    ແປງຂໍ້ມູນຄະແນນ (ເຊັ່ນ '2-1') ໃຫ້ຢູ່ໃນຮູບແບບ int
    """
    if not score_str or score_str == "-":
        return (None, None)
    try:
        parts = re.findall(r"\d+", score_str)
        if len(parts) >= 2:
            return (int(parts[0]), int(parts[1]))
    except:
        pass
    return (None, None)

def basic_stats(df):
    """
    ຄຳນວນສະຖິຕິພື້ນຖານຂອງທີມ
    """
    if df.empty:
        return {}
    
    df[["home_goals", "away_goals"]] = df["score"].apply(lambda x: pd.Series(parse_score(x)))
    total_goals = df["home_goals"].sum() + df["away_goals"].sum()
    avg_goals = total_goals / len(df) if len(df) > 0 else 0
    
    # ສະຖິຕິເຮືອນ-ເຢັນ
    home_wins = ((df["home_goals"] > df["away_goals"])).sum()
    away_wins = ((df["home_goals"] < df["away_goals"])).sum()
    draws = ((df["home_goals"] == df["away_goals"]) & (df["home_goals"].notna())).sum()
    
    return {
        "total_matches": len(df),
        "total_goals": total_goals,
        "avg_goals_per_match": round(avg_goals, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws
    }

def team_stats(df, team_name):
    """
    ສະຖິຕິສະເພາະທີມ
    """
    if df.empty:
        return {}
    df[["home_goals", "away_goals"]] = df["score"].apply(lambda x: pd.Series(parse_score(x)))
    home_matches = df[df["home_team"] == team_name]
    away_matches = df[df["away_team"] == team_name]
    
    goals_for = home_matches["home_goals"].sum() + away_matches["away_goals"].sum()
    goals_against = home_matches["away_goals"].sum() + away_matches["home_goals"].sum()
    matches_played = len(home_matches) + len(away_matches)
    
    return {
        "team": team_name,
        "matches": matches_played,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_diff": goals_for - goals_against,
        "avg_goals_for": round(goals_for / matches_played, 2) if matches_played > 0 else 0,
        "avg_goals_against": round(goals_against / matches_played, 2) if matches_played > 0 else 0
    }
