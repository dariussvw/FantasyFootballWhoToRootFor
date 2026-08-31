import streamlit as st
import requests
from datetime import datetime
import zoneinfo
from streamlit_autorun import autorun

# Seite konfigurieren
st.set_page_config(page_title="Fantasy Football - Who to root for?", layout="wide", initial_sidebar_state="collapsed")

# Auto-Refresh: Lädt die Seite alle 30 Sekunden (30.000 ms) automatisch neu
autorun(interval=30000)

st.title("🏈 Fantasy Football - Who to root for?")

# 1. Benutzer-Eingabe
username = st.text_input("Sleeper Username:", value="")

@st.cache_data(ttl=3600)
def get_nfl_players():
    """Lädt die gesamte Spieler-Datenbank von Sleeper."""
    res = requests.get("https://api.sleeper.app/v1/players/nfl")
    if res.status_code == 200:
        return res.json()
    return {}

@st.cache_data(ttl=60)
def get_current_nfl_state():
    """Holt die aktuelle Woche und Saison-Phase."""
    return requests.get("https://api.sleeper.app/v1/state/nfl").json()

def format_status_to_cet(status_detail, date_str):
    """Wandelt Spielzeiten/Datum in mitteleuropäische Zeit (CET/CEST) im 24h-Format um."""
    try:
        utc_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cet_dt = utc_dt.astimezone(zoneinfo.ZoneInfo("Europe/Berlin"))
        
        if "STATUS_SCHEDULED" in status_detail or "PM" in status_detail or "AM" in status_detail or "EDT" in status_detail or "EST" in status_detail:
            weekdays = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
            day_name = weekdays[cet_dt.weekday()]
            return f"{day_name} {cet_dt.strftime('%H:%M')} Uhr"
        return status_detail
    except Exception:
        return status_detail

@st.cache_data(ttl=60)
def get_nfl_schedule(week, season):
    """Holt den aktuellen NFL Spielplan und Live Scores von ESPN."""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&week={week}"
        res = requests.get(url).json()
        games = []
        for event in res.get("events", []):
            competition = event["competitions"][0]
            home_team = competition["competitors"][0]["team"]["abbreviation"]
            away_team = competition["competitors"][1]["team"]["abbreviation"]
            home_score = competition["competitors"][0].get("score", "0")
            away_score = competition["competitors"][1].get("score", "0")
            
            raw_status = event["status"]["type"]["shortDetail"]
            raw_type = event["status"]["type"]["name"]
            date_str = event.get("date", "")
            
            # Formatierung der Zeit für Deutschland
            if raw_type == "STATUS_SCHEDULED":
                status = format_status_to_cet(raw_type, date_str)
            else:
                status = raw_status

            # Umbenennen für Sleeper Kompatibilität
            alias = {"WSH": "WAS", "LAR": "LA", "NOP": "NO", "TBB": "TB"}
            home_team = alias.get(home_team, home_team)
            away_team = alias.get(away_team, away_team)
            
            games.append({
                "game_id": event["id"],
                "home_team": home_team,
                "away_team
