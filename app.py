import zoneinfo
from datetime import datetime

from espn_api.football import League as ESPNLeague
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Fantasy Football - Who to root for?",
    page_icon="logo.png",  # Favicon im Browser-Tab
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# STYLING & DESIGN (Fix für Matchup-Schriftfarbe)
# ---------------------------------------------------------
custom_css = """
<style>
    /* Haupt-Hintergrund & Textfarbe */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%) !important;
        color: #f0f6fc !important;
    }
    
    /* Helle Schrift für allgemeine Labels (Sprache, Inputs, Sidebar) */
    .stApp label, .stApp .stWidgetLabel, [data-testid="stSidebar"] * {
        color: #f0f6fc !important;
    }

    /* MATCHUP-EXPANDER: Schrift IMMER schwarz & fett (übersteuert den Dark Mode) */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {
        color: #000000 !important;
        font-weight: bold !important;
    }

    /* Haupt-Überschriften */
    h1, h2, h3, h4 {
        color: #58a6ff !important;
        font-weight: 800 !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }

    /* Input Felder (Textinputs, Radiobuttons) */
    .stTextInput input {
        background-color: #0d1117 !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    /* Buttons optisch aufwerten */
    .stButton > button {
        background: linear-gradient(90deg, #1f6feb 0%, #238636 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(31,111,235,0.4) !important;
    }

    /* Spieler-Karten (Container in den Expander-Elementen) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    
    /* Spieler-Texte innerhalb der vergrößerten Karten hell machen */
    [data-testid="stVerticalBlockBorderWrapper"] p, 
    [data-testid="stVerticalBlockBorderWrapper"] span {
        color: #f0f6fc !important;
    }

    /* Trennlinie & Captions */
    hr {
        border-color: #30363d !important;
    }
    .stCaption {
        color: #8b949e !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
# ---------------------------------------------------------

# 1. Sprache wählen
lang = st.radio(
    "Language / Sprache:", options=["DE", "EN"], horizontal=True, index=0
)
is_de = lang == "DE"

labels = {
    "title": "Fantasy Football - Who to root for?",
    "username": "Sleeper Username:",
    "week_overview": (
        "Woche {week} - Matchup Übersicht"
        if is_de
        else "Week {week} - Matchup Overview"
    ),
    "btn_collapse_all": "Alle zuklappen" if is_de else "Collapse All",
    "btn_expand_all": "Alle aufklappen" if is_de else "Expand All",
    "btn_live_only": (
        "Nur Live-Spiele aufklappen" if is_de else "Expand Live Games Only"
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
        " NFL-Spiele angesetzt."
        if is_de
        else (
            "Your players were loaded, but there are currently no NFL games"
            " scheduled for this week."
        )
    ),
    "tip_title": (
        "Tipp zum Speichern & Teilen:" if is_de else "Tip for Saving & Sharing:"
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

# Hauptbereich Header mit Logo & Titel
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("logo.png", use_container_width=True)
with col_title:
    st.title(labels["title"])

# Optionaler Bereich für öffentliche ESPN-Ligen in der Sidebar
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.header("Öffentliche ESPN Liga (Optional)")
espn_league_id = st.sidebar.text_input(
    "ESPN League ID:", value="", help="Nur für öffentliche ESPN-Ligen"
)
espn_team_name = st.sidebar.text_input("Dein ESPN Teamname:", value="")

# Sleeper Username ermitteln
query_params = st.query_params
DEFAULT_USER = "Schmitz"
initial_username = query_params.get("user", DEFAULT_USER)
username = st.text_input(labels["username"], value=initial_username)

if username:
    st.query_params["user"] = username

# Bei neuem Seitenaufruf standardmäßig alles eingeklappt
if "expand_mode" not in st.session_state:
    st.session_state.expand_mode = "none"


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

            status = (
                format_status_to_cet(raw_type, date_str, is_german)
                if raw_type == "STATUS_SCHEDULED"
                else raw_status
            )

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


def normalize_name(name):
    return (
        name.lower()
        .replace(".", "")
        .replace("'", "")
        .replace("-", " ")
        .replace(" jr", "")
        .replace(" sr", "")
        .strip()
    )


if username:
    with st.spinner(labels["loading"]):
        all_players = get_nfl_players()
        nfl_state = get_current_nfl_state()
        current_week = nfl_state.get("week", 1)
        season = nfl_state.get("season", "2026")

        name_to_sleeper_id = {}
        for pid, pdata in all_players.items():
            full_n = (
                f"{pdata.get('first_name', '')} {pdata.get('last_name', '')}"
            )
            if full_n.strip():
                name_to_sleeper_id[normalize_name(full_n)] = pid

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

            if not leagues and not espn_league_id:
                st.warning(labels["no_leagues"].format(season=season))

            player_data = {}

            # 1. Sleeper Ligen
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

            # 2. Öffentliche ESPN Liga
            if espn_league_id and espn_team_name:
                try:
                    espn_league = ESPNLeague(
                        league_id=int(espn_league_id), year=int(season)
                    )
                    espn_league_name = getattr(
                        espn_league.settings, "name", "ESPN League"
                    )

                    my_espn_team = next(
                        (
                            t
                            for t in espn_league.teams
                            if espn_team_name.lower() in t.team_name.lower()
                        ),
                        None,
                    )

                    if my_espn_team:
                        box_scores = espn_league.box_scores(current_week)
                        my_box = next(
                            (
                                b
                                for b in box_scores
                                if b.home_team == my_espn_team
                                or b.away_team == my_espn_team
                            ),
                            None,
                        )

                        if my_box:
                            is_home = my_box.home_team == my_espn_team
                            my_lineup = (
                                my_box.home_lineup
                                if is_home
                                else my_box.away_lineup
                            )
                            opp_lineup = (
                                my_box.away_lineup
                                if is_home
                                else my_box.home_lineup
                            )

                            for espn_player in my_lineup:
                                if espn_player.slot_position != "BE":
                                    norm_name = normalize_name(espn_player.name)
                                    s_pid = name_to_sleeper_id.get(norm_name)

                                    if s_pid:
                                        if s_pid not in player_data:
                                            p_info = all_players.get(s_pid, {})
                                            player_data[s_pid] = {
                                                "name": (
                                                    f"{p_info.get('first_name', '')}"
                                                    f" {p_info.get('last_name', s_pid)}"
                                                ),
                                                "pos": p_info.get(
                                                    "position", "DEF"
                                                ),
                                                "team": p_info.get(
                                                    "team", "FA"
                                                ),
                                                "my_leagues": [],
                                                "opp_leagues": [],
                                            }

                                        pts_str = f"{espn_player.points:.1f}"
                                        player_data[s_pid]["my_leagues"].append(
                                            f"ESPN: {espn_league_name} ({pts_str} Pts)"
                                        )

                            for espn_player in opp_lineup:
                                if espn_player.slot_position != "BE":
                                    norm_name = normalize_name(espn_player.name)
                                    s_pid = name_to_sleeper_id.get(norm_name)

                                    if s_pid:
                                        if s_pid not in player_data:
                                            p_info = all_players.get(s_pid, {})
                                            player_data[s_pid] = {
                                                "name": (
                                                    f"{p_info.get('first_name', '')}"
                                                    f" {p_info.get('last_name', s_pid)}"
                                                ),
                                                "pos": p_info.get(
                                                    "position", "DEF"
                                                ),
                                                "team": p_info.get(
                                                    "team", "FA"
                                                ),
                                                "my_leagues": [],
                                                "opp_leagues": [],
                                            }

                                        pts_str = f"{espn_player.points:.1f}"
                                        player_data[s_pid]["opp_leagues"].append(
                                            f"ESPN: {espn_league_name} ({pts_str} Pts)"
                                        )

                except Exception as e:
                    st.sidebar.error(f"Fehler bei ESPN: {e}")

            # 3. NFL-Schedule und Darstellung
            games = get_nfl_schedule(current_week, season, is_de)

            st.write(f"### {labels['week_overview'].format(week=current_week)}")

            col1, col2 = st.columns(2)
            with col1:
                btn_all_label = (
                    labels["btn_expand_all"]
                    if st.session_state.expand_mode == "none"
                    else labels["btn_collapse_all"]
                )
                if st.button(btn_all_label, use_container_width=True):
                    st.session_state.expand_mode = (
                        "all"
                        if st.session_state.expand_mode == "none"
                        else "none"
                    )
                    st.rerun()

            with col2:
                if st.button(labels["btn_live_only"], use_container_width=True):
                    st.session_state.expand_mode = "live_only"
                    st.rerun()

            if not games:
                st.warning(labels["no_live_games"])

            color_map_js = {}

            relevant_games = []
            for game in games:
                home = game["home_team"]
                away = game["away_team"]
                game_players = [
                    p
                    for p in player_data.values()
                    if p["team"] in [home, away]
                ]

                if game_players:
                    game_netto = sum(
                        len(p["my_leagues"]) - len(p["opp_leagues"])
                        for p in game_players
                    )
                    relevant_games.append({
                        "game": game,
                        "players": game_players,
                        "netto": game_netto,
                    })

            if relevant_games:
                for item in relevant_games:
                    game = item["game"]
                    game_players = item["players"]
                    netto = item["netto"]
                    away = game["away_team"]
                    home = game["home_team"]

                    if netto >= 3:
                        bg_color = "#d4edda"
                        border_color = "#c3e6cb"
                    elif netto in [1, 2]:
                        bg_color = "#e8f5e9"
                        border_color = "#a5d6a7"
                    elif netto in [-1, -2]:
                        bg_color = "#ffebee"
                        border_color = "#ef9a9a"
                    elif netto <= -3:
                        bg_color = "#f8d7da"
                        border_color = "#f5c6cb"
                    else:
                        bg_color = "#f8f9fa"
                        border_color = "#e0e0e0"

                    header_label = (
                        f"{away} @ {home} | {game['score']} ({game['status']})"
                    )

                    color_map_js[header_label] = (bg_color, border_color)

                    if st.session_state.expand_mode == "all":
                        is_expanded = True
                    elif st.session_state.expand_mode == "none":
                        is_expanded = False
                    elif st.session_state.expand_mode == "live_only":
                        is_expanded = game["is_live"]
                    else:
                        is_expanded = False

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
                            p_netto = my_cnt - opp_cnt

                            status = get_root_status(p_netto, is_de)

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

                # JS für fette schwarze Schrift & Matchup-Einfärbung im Light & Dark Mode
                js_script = "<script>"
                for title, (bg, border) in color_map_js.items():
                    escaped_title = title.replace("'", "\\'")
                    js_script += f"""
                    try {{
                        const summaries = window.parent.document.querySelectorAll('details summary');
                        summaries.forEach(el => {{
                            if (el.innerText.includes('{escaped_title}')) {{
                                el.style.backgroundColor = '{bg}';
                                el.style.border = '1px solid {border}';
                                el.style.borderRadius = '8px';
                                el.style.color = '#000000';
                                el.style.fontWeight = 'bold';
                            }}
                        }});
                    }} catch(e) {{ console.error(e); }}
                    """
                js_script += "</script>"
                components.html(js_script, height=0, width=0)

            elif player_data:
                st.info(labels["no_games_scheduled"])

            st.divider()
            st.caption(labels["tip_title"])
            st.caption(labels["tip_desc"])

else:
    st.info(labels["input_prompt"])

# Auto-Refresh alle 60 Sekunden
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
