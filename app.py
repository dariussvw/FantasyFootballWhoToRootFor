import zoneinfo
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(
    page_title="Fantasy Football - Who to root for?",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS für vergrößerte Matchup-Überschriften & farbige Expander
st.markdown(
    """
    <style>
    div[data-testid="stExpander"] details summary p {
        font-size: 1.25rem !important;
        font-weight: bold !important;
    }
    
    /* Farb-Klassen für die Expander-Hintergründe */
    div.expander-gruen details {
        background-color: #d4edda !important;
        border: 1px solid #c3e6cb !important;
        border-radius: 0.5rem;
    }
    div.expander-hell-gruen details {
        background-color: #e8f5e9 !important;
        border: 1px solid #a5d6a7 !important;
        border-radius: 0.5rem;
    }
    div.expander-hell-rot details {
        background-color: #ffebee !important;
        border: 1px solid #ef9a9a !important;
        border-radius: 0.5rem;
    }
    div.expander-rot details {
        background-color: #f8d7da !important;
        border: 1px solid #f5c6cb !important;
        border-radius: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 1. Sprache wählen
lang = st.radio(
    "Language / Sprache:", options=["DE", "EN"], horizontal=True, index=0
)
is_de = lang == "DE"

# Wörterbuch für Sprachausgaben
labels = {
    "title": "🏈 Fantasy Football - Who to root for?",
    "username": "Sleeper Username:",
    "week_overview": (
        "Woche {week} - Matchup Übersicht"
        if is_de
        else "Week {week} - Matchup Overview"
    ),
    "btn_collapse_all": "📁 Alle zuklappen" if is_de else "📁 Collapse All",
    "btn_expand_all": "📂 Alle aufklappen" if is_de else "📂 Expand All",
    "btn_live_only": (
        "🔴 Nur Live-Spiele aufklappen"
        if is_de
        else "🔴 Expand Live Games Only"
    ),
    "user_not_found": (
        "Sleeper-User '{username}' konnte nicht gefunden werden."
        if is_de
        else "Sleeper user '{username}' could not be found."
    ),
    "no_leagues": (
        "Keine Ligen für die Saison {season} gefunden."
        if is_de
        else "No leagues found for the {season} season."
    ),
    "no_live_games": (
        "Keine Live-Spiele für diese Woche gefunden."
        if is_de
        else "No live games found for this week."
    ),
    "loading": (
        "Lade Kader-, Live- und Punktestände..."
        if is_de
        else "Loading rosters, live scores, and stats..."
    ),
    "player": "Spieler" if is_de else "Player",
    "root": "Root?",
    "my_team": "Mein Team" if is_de else "My Team",
    "opponent": "Gegner" if is_de else "Opponent",
    "no_games_scheduled": (
        "Deine Spieler wurden geladen, aber für diese Woche sind aktuell keine"
        " NFL-Spiele angesetzt (z.B. Offseason / Preseason)."
        if is_de
        else (
            "Your players were loaded, but there are currently no NFL games"
            " scheduled for this week (e.g., Offseason / Preseason)."
        )
    ),
    "tip_title": (
        "💡 **Tipp zum Speichern & Teilen:**"
        if is_de
        else "💡 **Tip for Saving & Sharing:**"
    ),
    "tip_desc": (
        "Trage einfach deinen Sleeper-Namen ein. Die URL in deinem Browser passt"
        " sich automatisch an."
        if is_de
        else (
            "Just enter your Sleeper username. The URL in your browser will"
            " automatically update."
        )
    ),
    "input_prompt": (
        "Bitte gib oben deinen Sleeper-Usernamen ein."
        if is_de
        else "Please enter your Sleeper username above."
    ),
}

st.title(labels["title"])

# Username ermitteln
query_params = st.query_params
DEFAULT_USER = "Schmitz"

initial_username = query_params.get("user", DEFAULT_USER)
username = st.text_input(labels["username"], value=initial_username)

if username:
    st.query_params["user"] = username

# Session State Steuerung: 'all', 'none', oder 'live_only'
if "expand_mode" not in st.session_state:
    st.session_state.expand_mode = "all"


@st.cache_data(ttl=3600)
def get_nfl_players():
    res = requests.get("https://api.sleeper.app/v1/players/nfl")
    if res.status_code == 200:
        return res.json()
    return {}


@st.cache_data(ttl=60)
def get_current_nfl_state():
    res = requests.get("https://api.sleeper.app/v1/state/nfl")
    if res.status_code == 200:
        return res.json()
    return {"week": 1, "season": "2026"}


def format_status_to_cet(status_detail, date_str, is_german):
    try:
        utc_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cet_dt = utc_dt.astimezone(zoneinfo.ZoneInfo("Europe/Berlin"))

        if any(
            keyword in status_detail
            for keyword in ["STATUS_SCHEDULED", "PM", "AM", "EDT", "EST"]
        ):
            weekdays = (
                ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]
                if is_german
                else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            )
            day_name = weekdays[cet_dt.weekday()]
            return (
                f"{day_name} {cet_dt.strftime('%H:%M')} Uhr"
                if is_german
                else f"{day_name} {cet_dt.strftime('%H:%M')}"
            )
        return status_detail
    except Exception:
        return status_detail


@st.cache_data(ttl=60)
def get_nfl_schedule(week, season, is_german):
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

            is_live = raw_type == "STATUS_IN_PROGRESS" or (
                "STATUS_SCHEDULED" not in raw_type
                and "STATUS_FINAL" not in raw_type
                and raw_type != "STATUS_POSTPONED"
            )

            if raw_type == "STATUS_SCHEDULED":
                status = format_status_to_cet(raw_type, date_str, is_german)
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
                "is_live": is_live,
                "score": f"{away_team} {away_score} @ {home_team} {home_score}",
            })
        return games
    except Exception:
        return []


def get_root_status(netto, is_german):
    if is_german:
        if netto >= 3:
            return f"💦 ABFEUERN (+{netto})"
        elif netto == 2:
            return "🔥 JUBEL (+2)"
        elif netto == 1:
            return "🟢 GUTE (+1)"
        elif netto == 0:
            return "🤷 JUCKA (0)"
        elif netto == -1:
            return "🔴 DAMN (-1)"
        elif netto == -2:
            return "💀 FUCK (-2)"
        else:
            return f"🤬 CRASHOUT ({netto})"
    else:
        if netto >= 3:
            return f"💦 Shoot! (+{netto})"
        elif netto == 2:
            return "🔥 Root (+2)"
        elif netto == 1:
            return "🟢 Nice (+1)"
        elif netto ==
