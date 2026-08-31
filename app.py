import streamlit as st
import requests
from datetime import datetime
import zoneinfo
import time

st.set_page_config(page_title="Fantasy Football - Who to root for?", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS: Vergrößert die Schrift der Aufklapp-Header (Matchups) deutlich
st.markdown("""
    <style>
    .st-emotion-cache-1h9usn1, .st-emotion-cache-p5msec, div[data-testid="stExpander"] details summary p {
        font-size: 1.25rem !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏈 Fantasy Football - Who to root for?")

# 1. Username aus der URL auslesen oder Fallback verwenden
query_params = st.query_params

# TRAGE HIER DEINEN EIGENEN SLEEPER-NAMEN EIN (als Standard für dich):
DEFAULT_USER = "DEIN_SLEEPER_USERNAME" 

initial_username = query_params.get("user", DEFAULT_USER)

# Eingabefeld für den Benutzernamen
username = st.text_input("Sleeper Username:", value=initial_username)

if username:
    st.query_params["user"] = username

@st.cache_data(ttl=3600)
def get_nfl_players():
    res = requests.get("https://api.sleeper.app/v1/players/nfl")
    if res.status_code == 200:
        return res.json()
    return {}

@st.cache_data(ttl=60)
def get_current_nfl_state():
    return requests.get("https://api.sleeper.app/v1/state/nfl").json()

def format_status_to_cet(status_detail, date_str):
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
            
            if raw_type == "STATUS_SCHEDULED":
                status = format_status_to_cet(raw_type, date_str)
            else:
                status = raw_status

            alias = {"WSH": "WAS", "LAR": "LA", "NOP": "NO", "TBB": "TB"}
            home_team = alias.get(home_team, home_team)
            away_team = alias.get(away_team, away_team)
            
            games.append({
                "game_id": event["id"],
                "home_team": home_team,
                "away_team": away_team,
                "status": status,
                "score": f"{away_team} {away_score} @ {home_team} {home_score}"
            })
        return games
    except Exception:
        return []

if username:
    with st.spinner("Lade Kader- und Live-Daten..."):
        all_players = get_nfl_players()
        nfl_state = get_current_nfl_state()
        current_week = nfl_state.get("week", 1)
        season = nfl_state.get("season", "2026")
        
        user_res = requests.get(f"https://api.sleeper.app/v1/user/{username}").json()
        
        if not user_res or "user_id" not in user_res:
            st.error("User nicht gefunden.")
        else:
            user_id = user_res["user_id"]
            leagues = requests.get(f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}").json()
            
            player_data = {}
            
            for league in leagues:
                l_id = league["league_id"]
                l_name = league["name"]
                
                matchups = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/matchups/{current_week}").json()
                rosters = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/rosters").json()
                
                my_roster_id = next((r.get("roster_id") for r in rosters if r.get("owner_id") == user_id), None)
                if not my_roster_id or not matchups:
                    continue
                
                my_team_data = next((m for m in matchups if m and m.get("roster_id") == my_roster_id), None)
