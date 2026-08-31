import streamlit as st
import requests
from datetime import datetime
import zoneinfo
import time

st.set_page_config(page_title="Fantasy Football - Who to root for?", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS für vergrößerte Matchup-Überschriften
st.markdown("""
    <style>
    div[data-testid="stExpander"] details summary p {
        font-size: 1.25rem !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏈 Fantasy Football - Who to root for?")

# 1. Username ermitteln
query_params = st.query_params

DEFAULT_USER = "Schmitz"

initial_username = query_params.get("user", DEFAULT_USER)
username = st.text_input("Sleeper Username:", value=initial_username)

if username:
    st.query_params["user"] = username

# Session State für Auf-/Zuklappen aller Expandable Cards initialisieren
if "expand_all" not in st.session_state:
    st.session_state.expand_all = True

@st.cache_data(ttl=3600)
def get_nfl_players():
    res = requests.get("https://api.sleeper.app/v1/players/nfl")
    if res.status_code == 200:
        return res.json()
    return {}

@st.cache_data(ttl=30)
def get_current_nfl_state():
    res = requests.get("https://api.sleeper.app/v1/state/nfl")
    if res.status_code == 200:
        return res.json()
    return {"week": 1, "season": "2026"}

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

@st.cache_data(ttl=30)
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

if username and username != "DEIN_SLEEPER_USERNAME":
    with st.spinner("Lade Kader-, Live- und Punktestände..."):
        all_players = get_nfl_players()
        nfl_state = get_current_nfl_state()
        current_week = nfl_state.get("week", 1)
        season = nfl_state.get("season", "2026")
        
        user_res = requests.get(f"https://api.sleeper.app/v1/user/{username}").json()
        
        if not user_res or "user_id" not in user_res:
            st.error(f"Sleeper-User '{username}' konnte nicht gefunden werden.")
        else:
            user_id = user_res["user_id"]
            leagues = requests.get(f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}").json()
            
            if not leagues:
                st.warning(f"Keine Ligen für die Saison {season} gefunden.")
            
            player_data = {}
            
            for league in leagues:
                l_id = league["league_id"]
                l_name = league["name"]
                
                matchups = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/matchups/{current_week}").json()
                rosters = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/rosters").json()
                
                my_roster_id = next((r.get("roster_id") for r in rosters if r.get("owner_id") == user_id), None)
                if not my_roster_id:
                    continue
                
                my_team_data = next((m for m in matchups if m and m.get("roster_id") == my_roster_id), None) if matchups else None
                
                my_player_ids = []
                if my_team_data and my_team_data.get("starters"):
                    my_player_ids = [p for p in my_team_data.get("starters", []) if p and p != "0"]
                else:
                    my_roster_obj = next((r for r in rosters if r.get("roster_id") == my_roster_id), None)
                    if my_roster_obj and my_roster_obj.get("players"):
                        my_player_ids = my_roster_obj.get("players", [])

                my_pts_dict = my_team_data.get("players_points", {}) if my_team_data else {}

                for pid in my_player_ids:
                    if pid not in player_data:
                        p_info = all_players.get(pid, {})
                        player_data[pid] = {
                            "name": f"{p_info.get('first_name', '')} {p_info.get('last_name', pid)}",
                            "pos": p_info.get("position", "DEF"),
                            "team": p_info.get("team", "FA"),
                            "my_leagues": [],
                            "opp_leagues": []
                        }
                    
                    pts = my_pts_dict.get(pid, 0.0)
                    pts_str = f"{pts:.1f}" if pts is not None else "0.0"
                    player_data[pid]["my_leagues"].append(f"{l_name} ({pts_str} Pts)")

                if my_team_data:
                    my_matchup_id = my_team_data.get("matchup_id")
                    opp_team_data = next((m for m in matchups if m and m.get("matchup_id") == my_matchup_id and m.get("roster_id") != my_roster_id), None)
                    if opp_team_data:
                        opp_pids = opp_team_data.get("starters", []) if opp_team_data.get("starters") else opp_team_data.get("players", [])
                        opp_pts_dict = opp_team_data.get("players_points", {}) if opp_team_data else {}

                        for pid in opp_pids:
                            if pid and pid != "0":
                                if pid not in player_data:
                                    p_info = all_players.get(pid, {})
                                    player_data[pid] = {
                                        "name": f"{p_info.get('first_name', '')} {p_info.get('last_name', pid)}",
                                        "pos": p_info.get("position", "DEF"),
                                        "team": p_info.get("team", "FA"),
                                        "my_leagues": [],
                                        "opp_leagues": []
                                    }
                                
                                pts = opp_pts_dict.get(pid, 0.0)
                                pts_str = f"{pts:.1f}" if pts is not None else "0.0"
                                player_data[pid]["opp_leagues"].append(f"{l_name} ({pts_str} Pts)")

            games = get_nfl_schedule(current_week, season)

            # Header & Steuerungs-Button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"### Woche {current_week} - Matchup Übersicht")
            with col2:
                button_label = "📁 Alle zuklappen" if st.session_state.expand_all else "📂 Alle aufklappen"
                if st.button(button_label, use_container_width=True):
                    st.session_state.expand_all = not st.session_state.expand_all
                    st.rerun()

            if not games:
                st.warning("Keine Live-Spiele für diese Woche gefunden.")
            
            found_any_player = False
            for game in games:
                home = game["home_team"]
                away = game["away_team"]
                
                game_players = [
                    p for p in player_data.values() 
                    if p["team"] in [home, away]
                ]

                if game_players:
                    found_any_player = True
                    header_label = f"🏈 {away} @ {home} | {game['score']} ({game['status']})"
                    
                    with st.expander(header_label, expanded=st.session_state.expand_all):
                        game_players.sort(key=lambda p: (len(p["my_leagues"]) - len(p["opp_leagues"])), reverse=True)

                        for p in game_players:
                            my_cnt = len(p["my_leagues"])
                            opp_cnt = len(p["opp_leagues"])
                            netto = my_cnt - opp_cnt

                            if netto >= 3:
                                status = f"💦 ABFEUERN (+{netto})"
                            elif netto == 2:
                                status = "🔥 JUBEL (+2)"
                            elif netto == 1:
                                status = "🟢 GUTE (+1)"
                            elif netto == 0:
                                status = "🤷 JUCKA (0)"
                            elif netto == -1:
                                status = "🔴 DAMN (-1)"
                            elif netto == -2:
                                status = "💀 FUCK (-2)"
                            else:
                                status = f"🤬 CRASHOUT ({netto})"

                            with st.container(border=True):
                                st.markdown(f"**Spieler:** {p['name']} ({p['pos']}-{p['team']})")
                                st.markdown(f"**Auswirkung:** {status}")
                                
                                my_l_str = ", ".join(p["my_leagues"]) if p["my_leagues"] else "–"
                                opp_l_str = ", ".join(p["opp_leagues"]) if p["opp_leagues"] else "–"
                                
                                st.markdown(f"**Mein Team:** {my_l_str}")
                                st.markdown(f"**Gegner:** {opp_l_str}")

            if not found_any_player and player_data:
                st.info("Deine Spieler wurden geladen, aber für diese Woche sind aktuell keine NFL-Spiele angesetzt (z.B. Offseason / Preseason).")

            st.divider()
            st.caption("💡 **Tipp zum Speichern & Teilen:**")
            st.caption("Trage einfach deinen Sleeper-Namen ein. Die URL in deinem Browser passt sich automatisch an.")

else:
    st.info("Bitte gib oben deinen Sleeper-Usernamen ein.")

time.sleep(30)
st.rerun()
