import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. PAGE CONFIG (Muss als allererstes stehen!)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Fantasy Football Matchups",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. PWA META-TAGS (Für Smartphone App-Modus & Icon)
# ---------------------------------------------------------
pwa_meta = """
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Fantasy Hub">
<link rel="apple-touch-icon" href="https://img.icons8.com/emoji/192/american-football-emoji.png">
"""
st.markdown(pwa_meta, unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. CUSTOM CSS (Design, Lesbarkeit, Farben)
# ---------------------------------------------------------
custom_css = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161b22 100%) !important;
        color: #f0f6fc !important;
    }
    header[data-testid="stHeader"] {
        background-color: #161b22 !important;
    }
    .stApp label, .stApp .stWidgetLabel, [data-testid="stSidebar"] * {
        color: #f0f6fc !important;
    }
    div[data-testid="stRadio"] label p {
        color: #f0f6fc !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {
        color: #000000 !important;
        font-weight: bold !important;
    }
    h1, h2, h3, h4 {
        color: #58a6ff !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    .stTextInput input {
        background-color: #0d1117 !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
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
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] p, 
    [data-testid="stVerticalBlockBorderWrapper"] span {
        color: #f0f6fc !important;
    }
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
# 4. SIDEBAR & APP-INSTALL-BUTTON (Android & iOS)
# ---------------------------------------------------------
pwa_installer_html = """
<script>
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    document.getElementById('android-install-btn').style.display = 'block';
});

function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            deferredPrompt = null;
        });
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isAndroid = /Android/.test(navigator.userAgent);
    
    if (isIOS) {
        document.getElementById('ios-instructions').style.display = 'block';
    } else if (isAndroid && !deferredPrompt) {
        document.getElementById('android-fallback').style.display = 'block';
    }
});
</script>

<style>
    .install-card {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px;
        color: #f0f6fc;
        font-family: sans-serif;
    }
    .btn-install {
        background: linear-gradient(90deg, #1f6feb 0%, #238636 100%);
        color: white;
        border: none;
        padding: 10px;
        border-radius: 8px;
        font-weight: bold;
        cursor: pointer;
        width: 100%;
        margin-top: 8px;
    }
</style>

<div class="install-card">
    <div id="android-install-btn" style="display:none;">
        <p style="margin:0; font-size: 14px;">📱 <b>Als App installieren</b></p>
        <button class="btn-install" onclick="installPWA()">Auf Android installieren</button>
    </div>

    <div id="android-fallback" style="display:none;">
        <p style="margin:0; font-size: 14px;">📱 <b>Als App installieren:</b></p>
        <small style="color: #8b949e;">Tippe oben auf <b>(⋮)</b> & wähle <b>"App installieren"</b>.</small>
    </div>

    <div id="ios-instructions" style="display:none;">
        <p style="margin:0; font-size: 14px;">📱 <b>Als iPhone-App sichern:</b></p>
        <small style="color: #8b949e;">1. Tippe Safari <b>Teilen ⎋</b><br>2. <b>"Zum Home-Bildschirm"</b></small>
    </div>
</div>
"""

with st.sidebar:
    components.html(pwa_installer_html, height=120)
    st.divider()
    st.header("Einstellungen")
    username = st.text_input("Sleeper Username", value="")

# ---------------------------------------------------------
# 5. SESSION STATE FÜR EXPANDER (EINKLAPP-STEUERUNG)
# ---------------------------------------------------------
if "expander_state" not in st.session_state:
    st.session_state["expander_state"] = False

# ---------------------------------------------------------
# 6. HAUPTSEITE & MATCHUPS
# ---------------------------------------------------------
st.title("Fantasy Football Matchups")

# BEISPIEL: Matchup-Schleife (Hier fügst du deine API-Daten ein)
sample_matchups = [
    {"team1": "Düsseldorf Firecats", "team2": "Rival Team 1", "score1": "112.4", "score2": "108.1"},
    {"team1": "Manager 3", "team2": "Manager 4", "score1": "95.2", "score2": "120.6"},
]

for matchup in sample_matchups:
    title = f"🏈 {matchup['team1']} ({matchup['score1']}) vs {matchup['team2']} ({matchup['score2']})"
    
    with st.expander(title, expanded=st.session_state["expander_state"]):
        st.write(f"**Details für {matchup['team1']}**")
        st.write("• QB: Patrick Mahomes - Proj: 21.5")
        st.write("• RB: Christian McCaffrey - Proj: 18.2")
        st.divider()
        st.write(f"**Details für {matchup['team2']}**")
        st.write("• QB: Josh Allen - Proj: 22.0")

# ---------------------------------------------------------
# 7. BUTTONS AM SEITENENDE (EINKLAPPEN & HOCHSCROLLEN)
# ---------------------------------------------------------
st.divider()
col1, col2 = st.columns(2)

with col1:
    if st.button("📁 Alle einklappen & hochscrollen", use_container_width=True):
        st.session_state["expander_state"] = False
        components.html(
            """
            <script>
                window.parent.scrollTo({top: 0, behavior: 'smooth'});
            </script>
            """,
            height=0
        )
        st.rerun()

with col2:
    components.html(
        """
        <button onclick="window.parent.scrollTo({top: 0, behavior: 'smooth'});" 
                style="
                    width: 100%;
                    background: linear-gradient(90deg, #1f6feb 0%, #238636 100%);
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 8px;
                    font-weight: bold;
                    cursor: pointer;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                ">
            ⬆️ Nur hochscrollen
        </button>
        """,
        height=45
    )
