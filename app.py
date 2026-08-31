import streamlit as st
import streamlit.components.v1 as components

# 1. PAGE CONFIG (Muss ganz oben stehen!)
st.set_page_config(
    page_title="Fantasy Football Matchups",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. PWA META-TAGS (Für App-Icon & Vollbildmodus auf dem Smartphone)
pwa_meta = """
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Fantasy Hub">
<link rel="apple-touch-icon" href="https://img.icons8.com/emoji/192/american-football-emoji.png">
"""
st.markdown(pwa_meta, unsafe_allow_html=True)

# 3. CUSTOM CSS (Dein komplettes Styling inklusive Fixes für DE/EN, Top-Bar & schwarze Matchups)
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

# 4. SMART INSTALL-BUTTON (Am besten in der Sidebar platzieren!)
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

# Platziert die Installations-Karte ganz oben in der Sidebar:
with st.sidebar:
    components.html(pwa_installer_html, height=120)
    st.divider()

# ---------------------------------------------------------
# 5. AB HIER FOLGT DEIN NORMELER APP-CODE (Matchups, APIs, etc.)
# ---------------------------------------------------------
st.title("Fantasy Football Matchups")
# ... dein bisheriger Code ...
