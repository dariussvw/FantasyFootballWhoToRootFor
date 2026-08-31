import streamlit as st
import requests

st.set_page_config(page_title="Sleeper NFL Game Monitor", layout="wide", initial_sidebar_state="collapsed")

st.title("🏈 Sleeper Live NFL Game Monitor")

# 1. Eingabe
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
            status = event["status"]["type"]["shortDetail"]
            
            # Umbenennen für Sleeper Kompatibilität (z.B. WSH -> WAS, LAR -> LA)
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
        
        # User ID holen
        user_res = requests.get(f"https://api.sleeper.app/v1/user/{username}").json()
        
        if not user_res or "user_id" not in user_res:
            st.error("User nicht gefunden.")
        else:
            user_id = user_res["user_id"]
            
            # Alle Ligen laden
            leagues = requests.get(f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}").json()
            
            # Matrix: player_id -> Info
            player_data = {}
            
            for league in leagues:
                l_id = league["league_id"]
                l_name = league["name"]
                
                # Matchups der aktuellen Woche
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
                
                # Eigenes Team erfassen
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
                        
                # Gegner Team erfassen
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

            # NFL Live Schedule laden
            games = get_nfl_schedule(current_week, season)

            st.write(f"### Woche {current_week} - Matchup Übersicht")

            if not games:
                st.warning("Keine Live-Spiele für diese Woche gefunden oder Spielplan noch nicht geladen.")
            
            # Gruppierung nach NFL Spiel
            for game in games:
                home = game["home_team"]
                away = game["away_team"]
                
                # Filter alle Spieler, die in diesem NFL-Matchup spielen
                game_players = [
                    p for p in player_data.values() 
                    if p["team"] in [home, away]
                ]

                # Nur anzeigen, wenn mindestens 1 Spieler aus deinen Ligen in diesem Spiel am Start ist
                if game_players:
                    with st.expander(f"🏈 {away} @ {home} | {game['score']} ({game['status']})", expanded=True):
                        
                        table_data = []
                        for p in game_players:
                            my_cnt = len(p["my_leagues"])
                            opp_cnt = len(p["opp_leagues"])
                            netto = my_cnt - opp_cnt

                            # Neue Status-Logik
                            if netto >= 2:
                                status = f"🔥 JUBEL (+{netto})"
                            elif netto == 1:
                                status = "🟢 GUT (+1)"
                            elif netto == -1:
                                status = "🔴 SCHLECHT (-1)"
                            elif netto <= -2:
                                status = f"💥 KATASTROPHE ({netto})"
                            else:
                                status = "⚪ NEUTRAL (0)"

                            # Exakt festgelegte Spaltenreihenfolge
                            table_data.append({
                                "Spieler": f"{p['name']} ({p['pos']}-{p['team']})",
                                "Mein Team": ", ".join(p["my_leagues"]) if p["my_leagues"] else "-",
                                "Gegner": ", ".join(p["opp_leagues"]) if p["opp_leagues"] else "-",
                                "Auswirkung": status
                            })

                        # Spalten explizit sortieren & anzeigen
                        column_order = ["Spieler", "Mein Team", "Gegner", "Auswirkung"]
                        st.dataframe(
                            table_data, 
                            column_order=column_order,
                            use_container_width=True, 
                            hide_index=True
                        )
