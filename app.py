import zoneinfo
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(
    page_title="Fantasy Football - Who to root for?",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS für vergrößerte Matchup-Überschriften
st.markdown(
    """
    <style>
    div[data-testid="stExpander"] details summary p {
        font-size: 1.25rem !important;
        font-weight: bold !important;
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
        elif netto == 0:
            return "🤷 Wayne (0)"
        elif netto == -1:
            return "🔴 Damn (-1)"
        elif netto == -2:
            return "💀 Fuck (-2)"
        else:
            return f"🤬 Crashout ({netto})"


if username:
    with st.spinner(labels["loading"]):
        all_players = get_nfl_players()
        nfl_state = get_current_nfl_state()
        current_week = nfl_state.get("week", 1)
        season = nfl_state.get("season", "2026")

        user_res = requests.get(
            f"https://api.sleeper.app/v1/user/{username}"
        ).json()

        if not user_res or "user_id" not in user_res:
            st.error(labels["user_not_found"].format(username=username))
        else:
            user_id = user_res["user_id"]
            leagues = requests.get(
                f"https://api.sleeper.app/v1/user/{user_id}/leagues/nfl/{season}"
            ).json()

            if not leagues:
                st.warning(labels["no_leagues"].format(season=season))

            player_data = {}

            for league in leagues:
                l_id = league["league_id"]
                l_name = league["name"]

                matchups = requests.get(
                    f"https://api.sleeper.app/v1/league/{l_id}/matchups/{current_week}"
                ).json()
                rosters = requests.get(
                    f"https://api.sleeper.app/v1/league/{l_id}/rosters"
                ).json()

                my_roster_id = next(
                    (
                        r.get("roster_id")
                        for r in rosters
                        if r.get("owner_id") == user_id
                    ),
                    None,
                )
                if not my_roster_id:
                    continue

                my_team_data = (
                    next(
                        (
                            m
                            for m in matchups
                            if m and m.get("roster_id") == my_roster_id
                        ),
                        None,
                    )
                    if matchups
                    else None
                )

                my_player_ids = []
                if my_team_data and my_team_data.get("starters"):
                    my_player_ids = [
                        p
                        for p in my_team_data.get("starters", [])
                        if p and p != "0"
                    ]
                else:
                    my_roster_obj = next(
                        (
                            r
                            for r in rosters
                            if r.get("roster_id") == my_roster_id
                        ),
                        None,
                    )
                    if my_roster_obj and my_roster_obj.get("players"):
                        my_player_ids = my_roster_obj.get("players", [])

                my_pts_dict = (
                    my_team_data.get("players_points", {})
                    if my_team_data
                    else {}
                )

                for pid in my_player_ids:
                    if pid not in player_data:
                        p_info = all_players.get(pid, {})
                        player_data[pid] = {
                            "name": (
                                f"{p_info.get('first_name', '')}"
                                f" {p_info.get('last_name', pid)}"
                            ),
                            "pos": p_info.get("position", "DEF"),
                            "team": p_info.get("team", "FA"),
                            "my_leagues": [],
                            "opp_leagues": [],
                        }

                    pts = my_pts_dict.get(pid, 0.0)
                    pts_str = f"{pts:.1f}" if pts is not None else "0.0"
                    player_data[pid]["my_leagues"].append(
                        f"{l_name} ({pts_str} Pts)"
                    )

                if my_team_data:
                    my_matchup_id = my_team_data.get("matchup_id")
                    opp_team_data = next(
                        (
                            m
                            for m in matchups
                            if m
                            and m.get("matchup_id") == my_matchup_id
                            and m.get("roster_id") != my_roster_id
                        ),
                        None,
                    )
                    if opp_team_data:
                        opp_pids = (
                            opp_team_data.get("starters", [])
                            if opp_team_data.get("starters")
                            else opp_team_data.get("players", [])
                        )
                        opp_pts_dict = (
                            opp_team_data.get("players_points", {})
                            if opp_team_data
                            else {}
                        )

                        for pid in opp_pids:
                            if pid and pid != "0":
                                if pid not in player_data:
                                    p_info = all_players.get(pid, {})
                                    player_data[pid] = {
                                        "name": (
                                            f"{p_info.get('first_name', '')}"
                                            f" {p_info.get('last_name', pid)}"
                                        ),
                                        "pos": p_info.get("position", "DEF"),
                                        "team": p_info.get("team", "FA"),
                                        "my_leagues": [],
                                        "opp_leagues": [],
                                    }

                                pts = opp_pts_dict.get(pid, 0.0)
                                pts_str = (
                                    f"{pts:.1f}" if pts is not None else "0.0"
                                )
                                player_data[pid]["opp_leagues"].append(
                                    f"{l_name} ({pts_str} Pts)"
                                )

            games = get_nfl_schedule(current_week, season, is_de)

            st.write(f"### {labels['week_overview'].format(week=current_week)}")

            # Steuerungselemente: Buttons nebeneinander
            col1, col2 = st.columns(2)
            with col1:
                btn_all_label = (
                    labels["btn_collapse_all"]
                    if st.session_state.expand_mode == "all"
                    else labels["btn_expand_all"]
                )
                if st.button(btn_all_label, use_container_width=True):
                    st.session_state.expand_mode = (
                        "none"
                        if st.session_state.expand_mode == "all"
                        else "all"
                    )
                    st.rerun()

            with col2:
                if st.button(labels["btn_live_only"], use_container_width=True):
                    st.session_state.expand_mode = "live_only"
                    st.rerun()

            if not games:
                st.warning(labels["no_live_games"])

            found_any_player = False
            for game in games:
                home = game["home_team"]
                away = game["away_team"]

                game_players = [
                    p
                    for p in player_data.values()
                    if p["team"] in [home, away]
                ]

                if game_players:
                    found_any_player = True
                    header_label = f"🏈 {away} @ {home} | {game['score']} ({game['status']})"

                    if st.session_state.expand_mode == "all":
                        is_expanded = True
                    elif st.session_state.expand_mode == "none":
                        is_expanded = False
                    elif st.session_state.expand_mode == "live_only":
                        is_expanded = game["is_live"]
                    else:
                        is_expanded = True

                    with st.expander(header_label, expanded=is_expanded):
                        game_players.sort(
                            key=lambda p: (
                                len(p["my_leagues"]) - len(p["opp_leagues"])
                            ),
                            reverse=True,
                        )

                        for p in game_players:
                            my_cnt = len(p["my_leagues"])
                            opp_cnt = len(p["opp_leagues"])
                            netto = my_cnt - opp_cnt

                            status = get_root_status(netto, is_de)

                            with st.container(border=True):
                                st.markdown(
                                    f"**{labels['player']}:** {p['name']}"
                                    f" ({p['pos']}-{p['team']})"
                                )
                                st.markdown(f"**{labels['root']}:** {status}")

                                my_l_str = (
                                    ", ".join(p["my_leagues"])
                                    if p["my_leagues"]
                                    else "–"
                                )
                                opp_l_str = (
                                    ", ".join(p["opp_leagues"])
                                    if p["opp_leagues"]
                                    else "–"
                                )

                                st.markdown(
                                    f"**{labels['my_team']}:** {my_l_str}"
                                )
                                st.markdown(
                                    f"**{labels['opponent']}:** {opp_l_str}"
                                )

            if not found_any_player and player_data:
                st.info(labels["no_games_scheduled"])

            st.divider()
            st.caption(labels["tip_title"])
            st.caption(labels["tip_desc"])

else:
    st.info(labels["input_prompt"])

# Auto-Refresh alle 60 Sekunden (Clientseitig via JS, ohne Server-Thread zu blockieren)
st.markdown(
    """
    <script>
        setTimeout(function(){
            window.location.reload();
        }, 60000);
    </script>
""",
    unsafe_allow_html=True,
)
