import asyncio
import datetime
from typing import Dict, List, Tuple

import aiohttp
import pytz
import requests
import streamlit as st
from tzlocal import get_localzone

# ==========================================
# 1. CONFIG & SYSTEM TIMEZONE
# ==========================================
st.set_page_config(
    page_title="Sleeper Rooting Dashboard", page_icon="🏈", layout="wide"
)

# Automatische Erkennung der System-Zeitzone
try:
    LOCAL_TZ = get_localzone()
except Exception:
    LOCAL_TZ = pytz.timezone("Europe/Berlin")


# ==========================================
# 2. OPTIMALES CACHING (SPEICHER-EFFIZIENT)
# ==========================================
@st.cache_data(ttl=86400, show_spinner="Lade NFL-Spielerdatenbank...")
def get_optimized_players_db() -> Dict[str, Dict[str, str]]:
    """Lädt die Sleeper-Spielerdatenbank und reduziert sie auf minimale Attribute,

    um den RAM-Verbrauch extrem gering zu halten.
    """
    url = "https://api.sleeper.app/v1/players/nfl"
    response = requests.get(url)
    if response.status_code != 200:
        return {}

    raw_data = response.json()
    optimized_db = {}

    for player_id, info in raw_data.items():
        # Nur relevante Positions- und Namensdaten extrahieren
        pos = info.get("position")
        if pos in ["QB", "RB", "WR", "TE", "K", "DEF"]:
            first_name = info.get("first_name", "")
            last_name = info.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = info.get("search_full_name", player_id)

            optimized_db[player_id] = {
                "name": full_name,
                "position": pos,
                "team": info.get("team") or "FA",
            }
    return optimized_db


# ==========================================
# 3. ASYNCHRONE API-ABRUFE (SPEED & PERFORMANCE)
# ==========================================
async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict:
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.json()
    except Exception:
        pass
    return {}


async def fetch_all_sleeper_data(username: str, season: str) -> Tuple[dict, list, list]:
    async with aiohttp.ClientSession() as session:
        # 1. User ID holen
        user_url = f"https://api.sleeper.app/v1/user/{username}"
        user_data = await fetch_json(session, user_url)
        if not user_data or "user_id" not in user_data:
            return {}, [], []

        user_id = user_data["user_id"]

        # 2. Ligen des Users holen
        leagues_url = f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}"
        leagues = await fetch_json(session, leagues_url)
        if not isinstance(leagues, list):
            return user_data, [], []

        # 3. Paralleler Abruf aller Rosters und aktuellen Matchups aller Ligen
        matchup_tasks = []
        roster_tasks = []
        for league in leagues:
            l_id = league["league_id"]
            # Aktuelle Woche aus der Liga holen oder Standard 1
            current_week = league.get("settings", {}).get("leg", 1)

            roster_tasks.append(
                fetch_json(
                    session, f"https://api.sleeper.app/v1/league/{l_id}/rosters"
                )
            )
            matchup_tasks.append(
                fetch_json(
                    session,
                    f"https://api.sleeper.app/v1/league/{l_id}/matchups/{current_week}",
                )
            )

        rosters_results = await asyncio.gather(*roster_tasks)
        matchups_results = await asyncio.gather(*matchup_tasks)

        # Zuordnung zu den Ligen herstellen
        for idx, league in enumerate(leagues):
            league["_rosters"] = rosters_results[idx]
            league["_matchups"] = matchups_results[idx]

        return user_data, leagues, user_id


# ==========================================
# 4. ESPN RED ZONE & POSSESSION TRACKER
# ==========================================
def get_espn_live_tracker() -> Dict[str, dict]:
    """Holt die Live-Spieldaten inklusive Red Zone & Ballbesitz von ESPN."""
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return {}
        data = res.json()

        game_status = {}
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            status = event.get("status", {})
            situation = competition.get("situation", {})

            # Possession & Redzone Status
            possession_team_id = situation.get("possession")
            is_redzone = situation.get("isRedZone", False)

            # Details zu Heim- und Auswärtsteam
            teams_info = {}
            for competitor in competition.get("competitors", []):
                team_abbr = competitor.get("team", {}).get("abbreviation")
                team_id = competitor.get("team", {}).get("id")
                score = competitor.get("score", "0")
                has_possession = team_id == possession_team_id

                teams_info[team_abbr] = {
                    "score": score,
                    "possession": has_possession,
                    "redzone": has_possession and is_redzone,
                }

            # Zeit- / Quarter-Status
            clock = status.get("displayClock", "0:00")
            period = status.get("period", 0)
            state = status.get("type", {}).get("state", "pre")  # pre, in, post

            # Startzeit in lokaler Zeitzone formatieren
            utc_date_str = event.get("date")
            formatted_time = ""
            if utc_date_str:
                dt = datetime.datetime.fromisoformat(
                    utc_date_str.replace("Z", "+00:00")
                )
                local_dt = dt.astimezone(LOCAL_TZ)
                formatted_time = local_dt.strftime("%a %H:%M")

            for team_abbr, details in teams_info.items():
                game_status[team_abbr] = {
                    "state": state,
                    "clock": clock,
                    "period": period,
                    "start_time": formatted_time,
                    "possession": details["possession"],
                    "redzone": details["redzone"],
                    "team_details": teams_info,
                }

        return game_status
    except Exception:
        return {}


# ==========================================
# 5. UI & HAUPTLOGIK
# ==========================================
def main():
    st.title("🏈 Sleeper Root-Score & Live Tracker")
    st.caption(f"System-Zeitzone erkannt: **{LOCAL_TZ}**")

    # Sidebar Config
    st.sidebar.header("Einstellungen")
    username = st.sidebar.text_input("Sleeper Username", value="")
    season = st.sidebar.text_input("Saison", value="2026")

    if not username:
        st.info(
            "Bitte gib deinen Sleeper-Usernamen in der Seitenleiste ein, um zu starten."
        )
        return

    # 1. Spielerdatenbank laden (optimiert im Cache)
    players_db = get_optimized_players_db()

    # 2. Daten asynchron laden
    with st.spinner("Lade Liga- und Matchupdaten..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user_data, leagues, user_id = loop.run_until_complete(
            fetch_all_sleeper_data(username, season)
        )

    if not leagues:
        st.error(
            "Keine Ligen gefunden oder Fehler beim Abruf der Nutzerdaten."
        )
        return

    # 3. ESPN Live Tracker laden
    espn_status = get_espn_live_tracker()

    # 4. Root-Score-Berechnung
    player_scores = {}  # {player_id: {"score": int, "for": [], "against": []}}

    for league in leagues:
        rosters = league.get("_rosters", [])
        matchups = league.get("_matchups", [])

        # Eigenen Roster & Matchup finden
        my_roster = next(
            (r for r in rosters if r.get("owner_id") == user_id), None
        )
        if not my_roster:
            continue

        my_roster_id = my_roster.get("roster_id")
        my_matchup = next(
            (m for m in matchups if m.get("roster_id") == my_roster_id), None
        )
        if not my_matchup:
            continue

        matchup_id = my_matchup.get("matchup_id")
        opp_matchup = next(
            (
                m
                for m in matchups
                if m.get("matchup_id") == matchup_id
                and m.get("roster_id") != my_roster_id
            ),
            None,
        )

        my_starters = set(my_matchup.get("starters") or [])
        opp_starters = set(opp_matchup.get("starters") or []) if opp_matchup else set()

        # Eigene Starter -> Pro (+1)
        for pid in my_starters:
            if pid not in player_scores:
                player_scores[pid] = {
                    "score": 0,
                    "pro_leagues": [],
                    "con_leagues": [],
                }
            player_scores[pid]["score"] += 1
            player_scores[pid]["pro_leagues"].append(league.get("name"))

        # Gegner-Starter -> Contra (-1)
        for pid in opp_starters:
            if pid not in player_scores:
                player_scores[pid] = {
                    "score": 0,
                    "pro_leagues": [],
                    "con_leagues": [],
                }
            player_scores[pid]["score"] -= 1
            player_scores[pid]["con_leagues"].append(league.get("name"))

    # ==========================================
    # DASHBOARD: HEUTIGE TOP-ROOTING-SPIELER
    # ==========================================
    st.subheader("🔥 Top-Rooting-Prioritäten")

    sorted_players = sorted(
        player_scores.items(), key=lambda x: x[1]["score"], reverse=True
    )

    top_pro = [p for p in sorted_players if p[1]["score"] > 0][:3]
    top_con = [p for p in sorted_players if p[1]["score"] < 0][-3:]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💦 Anfeuern (Top Need)")
        if not top_pro:
            st.write("Keine klaren Favoriten zum Anfeuern.")
        for pid, data in top_pro:
            p_info = players_db.get(
                pid, {"name": pid, "position": "-", "team": "-"}
            )
            st.success(
                f"**{p_info['name']}** ({p_info['position']} - {p_info['team']})  \n"
                f"👉 **Root-Score: +{data['score']}** (In {len(data['pro_leagues'])} Ligen auf Deiner Seite)"
            )

    with col2:
        st.markdown("### 🛑 Hassen (Top Danger)")
        if not top_con:
            st.write("Keine klaren gegnerischen Bedrohungen.")
        for pid, data in reversed(top_con):
            p_info = players_db.get(
                pid, {"name": pid, "position": "-", "team": "-"}
            )
            st.error(
                f"**{p_info['name']}** ({p_info['position']} - {p_info['team']})  \n"
                f"👉 **Root-Score: {data['score']}** (Gegen dich gestartet in {len(data['con_leagues'])} Ligen)"
            )

    st.divider()

    # ==========================================
    # DETALLIERTE LISTE ALLER SPIELER MIT ESPN-LIVE TRACKER
    # ==========================================
    st.subheader("📋 Alle relevanten Spieler des Spieltags")

    for pid, data in sorted_players:
        p_info = players_db.get(
            pid, {"name": pid, "position": "DEF", "team": pid}
        )
        team = p_info["team"]

        # ESPN-Live Info abgreifen
        live_info = espn_status.get(team, {})
        status_text = ""

        if live_info:
            state = live_info.get("state")
            if state == "in":
                pos_str = " 🏈" if live_info.get("possession") else ""
                rz_str = " 🚨 **RED ZONE**" if live_info.get("redzone") else ""
                status_text = f"🟢 LIVE - Q{live_info.get('period')} {live_info.get('clock')}{pos_str}{rz_str}"
            elif state == "post":
                status_text = "🏁 FINAL"
            else:
                status_text = f"⏰ {live_info.get('start_time', 'Demnächst')}"
        else:
            status_text = "⏰ Keines der ESPN-Spiele zugeordnet"

        score = data["score"]
        score_badge = (
            f"🟢 **+{score}**"
            if score > 0
            else (f"🔴 **{score}**" if score < 0 else "⚪ **0**")
        )

        with st.expander(
            f"{p_info['name']} ({p_info['position']} - {team}) | Root-Score: {score_badge} | {status_text}"
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Dafür gestartet in:**")
                for l in data["pro_leagues"]:
                    st.write(f"- {l}")
            with c2:
                st.write("**Dagegen gestartet in:**")
                for l in data["con_leagues"]:
                    st.write(f"- {l}")


if __name__ == "__main__":
    main()
