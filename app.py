import streamlit as st
import requests
from datetime import datetime
import zoneinfo
import time

st.set_page_config(page_title="Fantasy Football - Who to root for?", layout="wide", initial_sidebar_state="collapsed")

st.title("🏈 Fantasy Football - Who to root for?")

# 1. Username aus der URL auslesen oder Fallback verwenden
query_params = st.query_params

# TRAGE HIER DEINEN EIGENEN SLEEPER-NAMEN EIN (als Standard für dich):
DEFAULT_USER = "DEIN_SLEEPER_USERNAME" 

# Priorität: 1. Name aus URL (?user=...), 2. DEINT_SLEEPER_USERNAME, 3. Leer
initial_username = query_params.get("user", DEFAULT_USER)

# Eingabefeld für den Benutzernamen
username = st.text_input("Sleeper Username:", value=initial_username)

# Wenn ein Name eingegeben ist, erstelle einen persönlichen Teilen-Link
if username:
    # Aktualisiert die URL im Browser, damit man die Seite direkt als Lesezeichen speichern kann
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
                if not my_team_data:
                    continue

                my_matchup_id = my_team_data.get("matchup_id")
                opp_team_data = next((m for m in matchups if m and m.get("matchup_id") == my_matchup_id and m.get("roster_id") != my_roster_id), None)
                
                for pid in my_team_data.get("starters", []):
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
                        player_data[pid]["my_leagues"].append(l_name)
                        
                if opp_team_data:
                    for pid in opp_team_data.get("starters", []):
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
                            player_data[pid]["opp_leagues"].append(l_name)

            games = get_nfl_schedule(current_week, season)

            st.write(f"### Woche {current_week} - Matchup Übersicht")

            if not games:
                st.warning("Keine Live-Spiele für diese Woche gefunden.")
            
            for game in games:
                home = game["home_team"]
                away = game["away_team"]
                
                game_players = [
                    p for p in player_data.values() 
                    if p["team"] in [home, away]
                ]

                if game_players:
                    with st.expander(f"🏈 {away} @ {home} | {game['score']} ({game['status']})", expanded=True):
                        table_data = []
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

                            table_data.append({
                                "Spieler": f"{p['name']} ({p['pos']}-{p['team']})",
                                "Mein Team": ", ".join(p["my_leagues"]) if p["my_leagues"] else "-",
                                "Gegner": ", ".join(p["opp_leagues"]) if p["opp_leagues"] else "-",
                                "Auswirkung": status
                            })

                        column_order = ["Spieler", "Mein Team", "Gegner", "Auswirkung"]
                        st.dataframe(
                            table_data, 
                            column_order=column_order,
                            use_container_width=True, 
                            hide_index=True
                        )

            # Hinweis für Freunde / Lesezeichen
            st.divider()
            st.caption("💡 **Tipp zum Speichern & Teilen:**")
            st.caption(f"Trage einfach oben deinen Sleeper-Namen ein. Die URL in deinem Browser passt sich automatisch an. Wenn du dir diese URL als Favorit oder auf deinem Smartphone-Startbildschirm abspeicherst, öffnet sich die App jedes Mal direkt mit deinen Daten!")

    # Sicheres Auto-Refresh ohne Extra-Paket (alle 60 Sekunden)
    time.sleep(60)
    st.rerun()
