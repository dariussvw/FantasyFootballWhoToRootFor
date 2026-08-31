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
        res =
