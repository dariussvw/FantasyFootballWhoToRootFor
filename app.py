import streamlit as st
import requests

st.set_page_config(page_title="Sleeper Multi-League Live Matrix", layout="wide")

st.title("🏈 Sleeper Multi-League Matchup Dashboard")

# 1. Benutzer-Eingabe
col1, col2 = st.columns([2, 1])
with col1:
    username = st.text_input("Sleeper Username:", value="")
with col2:
    year = st.selectbox("Saison:", ["2026", "2025"], index=0)

@st.cache_data(ttl=3600)
def get_nfl_players():
    """Lädt die gesamte Spieler-Datenbank von Sleeper (Namen & Positionen)."""
    url = "https://api.sleeper.app/v1/players/nfl"
    res = requests.get(url)
    if res.status_code == 200:
        return res.json()
    return {}

@st.cache_data(ttl=60)
def get_current_week():
    """Ermittelt die aktuelle NFL-Woche."""
    res = requests.get("https://api.sleeper.app/v1/state/nfl").json()
    return res.get("week", 1)

if username:
    with st.spinner("Lade Liga- und Spielerdaten..."):
        all_players = get_nfl_players()
        current_week = get_current_week()
        
        # User ID holen
        user_res = requests.get(f"https://api.sleeper.app/v1/user/{username}").json()
        
        if not user_res or "user_id" not in user_res:
            st.error("User nicht gefunden. Bitte überprüfe den Usernamen.")
        else:
            user_id = user_res["user_id"]
            
            # Alle Ligen des Users laden
            leagues_url = f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{year}"
            leagues = requests.get(leagues_url).json()

            st.subheader(f"Gefunden: {len(leagues)} Ligen (Woche {current_week})")

            # Datenstruktur für die Aggregation
            # player_id -> { "name": ..., "pos": ..., "my_leagues": [], "opp_leagues": [] }
            matrix = {}

            for league in leagues:
                l_id = league["league_id"]
                l_name = league["name"]

                # Matchups der aktuellen Woche holen
                matchups = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/matchups/{current_week}").json()
                
                # Eigenes Team ermitteln
                my_matchup = next((m for m in matchups if m and m.get("roster_id") is not None), None)
                
                # Roster-ID-Zuordnung laden, um herauszufinden welche roster_id dem User gehört
                rosters = requests.get(f"https://api.sleeper.app/v1/league/{l_id}/rosters").json()
                my_roster_id = None
                for r in rosters:
                    if r.get("owner_id") == user_id:
                        my_roster_id = r.get("roster_id")
                        break

                if not my_roster_id:
                    continue

                # Eigenes Matchup-Objekt und das des Gegners finden
                my_team_data = next((m for m in matchups if m.get("roster_id") == my_roster_id), None)
                if not my_team_data:
                    continue

                my_matchup_id = my_team_data.get("matchup_id")
                opp_team_data = next((m for m in matchups if m.get("matchup_id") == my_matchup_id and m.get("roster_id") != my_roster_id), None)

                # 1. Eigene Starter eintragen
                for pid in my_team_data.get("starters", []):
                    if pid and pid != "0":
                        if pid not in matrix:
                            p_info = all_players.get(pid, {})
                            matrix[pid] = {
                                "name": f"{p_info.get('first_name', '')} {p_info.get('last_name', pid)}",
                                "pos": p_info.get("position", "DEF"),
                                "team": p_info.get("team", "FA"),
                                "my_leagues": [],
                                "opp_leagues": []
                            }
                        matrix[pid]["my_leagues"].append(l_name)

                # 2. Gegner-Starter eintragen
                if opp_team_data:
                    for pid in opp_team_data.get("starters", []):
                        if pid and pid != "0":
                            if pid not in matrix:
                                p_info = all_players.get(pid, {})
                                matrix[pid] = {
                                    "name": f"{p_info.get('first_name', '')} {p_info.get('last_name', pid)}",
                                    "pos": p_info.get("position", "DEF"),
                                    "team": p_info.get("team", "FA"),
                                    "my_leagues": [],
                                    "opp_leagues": []
                                }
                            matrix[pid]["opp_leagues"].append(l_name)

            # Darstellung der Ergebnisse
            table_data = []
            for pid, pdata in matrix.items():
                my_count = len(pdata["my_leagues"])
                opp_count = len(pdata["opp_leagues"])
                netto = my_count - opp_count

                # Optische Bewertung für Touchdowns
                if netto > 0:
                    status = f"🟢 JUBELN (+{netto})"
                elif netto < 0:
                    status = f"🔴 FLUCHEN ({netto})"
                else:
                    status = "⚪ NEUTRAL (0)"

                table_data.append({
                    "NFL-Spieler": pdata["name"],
                    "Pos": pdata["pos"],
                    "NFL Team": pdata["team"],
                    "Bei dir SXI": ", ".join(pdata["my_leagues"]) if pdata["my_leagues"] else "-",
                    "Beim Gegner SXI": ", ".join(pdata["opp_leagues"]) if pdata["opp_leagues"] else "-",
                    "Netto-Auswirkung": status
                })

            st.dataframe(table_data, use_container_width=True)
