# scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def fetch_live_matches(mark="th", width=700):
    """
    ດຶງຂໍ້ມູນການແຂ່ງຂັນຈາກ 7m live score
    """
    url = f"https://freelive.7mth2.com/live.aspx?mark={mark}&width={width}&TimeZone=%2B0700"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # ຊອກຫາຕາຕະລາງ (ສ່ວນນີ້ອາດຕ້ອງປັບຕາມ HTML ຈິງ)
        rows = []
        for row in soup.select("table tr"):  # ປັບ selector ໃຫ້ກົງກັບໂຄງສ້າງຂອງເວັບ
            cells = row.find_all("td")
            if len(cells) >= 5:
                league = cells[0].get_text(strip=True) if cells[0] else ""
                time = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                home_team = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                score = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                away_team = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                rows.append([league, time, home_team, score, away_team])
        
        df = pd.DataFrame(rows, columns=["league", "time", "home_team", "score", "away_team"])
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()
