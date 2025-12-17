# main.py — Phonics Phorest home (full background + centered Start)
import base64, os
import streamlit as st

st.set_page_config(
    page_title="BrighterText – Phonics Phorest",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def _b64(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# --- EXPECTED LOCATIONS (same folder as main.py) ---
BG_PATHS   = ["phonics_phorest.png", "assets/phonics_phorest.png"]
BEAR_PATHS = ["waving_bear.png", "assets/waving_bear.png"]

def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

bg_file   = _first_existing(BG_PATHS)
bear_file = _first_existing(BEAR_PATHS)

bg_b64   = _b64(bg_file)   if bg_file   else None
bear_b64 = _b64(bear_file) if bear_file else None

# --- CSS: apply background to the correct Streamlit container ---
if bg_b64:
    st.markdown(
        f"""
        <style>
        /* Hide chrome */
        header, footer {{ visibility: hidden; }}
        [data-testid="stSidebar"] {{ display: none; }}
        .block-container {{ padding: 0; margin: 0; max-width: 100%; }}

        /* Full-page background on the app view container (most reliable) */
        [data-testid="stAppViewContainer"] {{
          background-image: url("data:image/png;base64,{bg_b64}");
          background-size: cover;
          background-position: center;
          background-repeat: no-repeat;
        }}

        /* Centered Start button */
        .center-wrap {{
          position: fixed;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
        }}
        .start-btn {{
          font-size: 24px;
          padding: 18px 40px;
          border-radius: 20px;
          border: none;
          background: #ffffffee;
          cursor: pointer;
          font-weight: 700;
          color: #1b4d2b;
          box-shadow: 0 6px 16px rgba(0,0,0,0.25);
          transition: transform .12s ease, background .12s ease;
        }}
        .start-btn:hover {{ background:#dfffe3; transform: scale(1.05); }}

        /* Waving bear, bottom-right */
        .waving-bear {{
          position: fixed;
          right: 20px;
          bottom: 20px;
          height: 120px;
          z-index: 11;
          transform-origin: bottom left;
          animation: wave 1s ease-in-out infinite alternate;
        }}
        @keyframes wave {{ 0% {{transform: rotate(0deg)}} 100% {{transform: rotate(15deg)}} }}
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.error(
        "Background image not found. Place **phonics_phorest.png** in the same folder as `main.py` "
        "(or `assets/phonics_phorest.png`)."
    )

# --- Centered Start button that routes to /game (pages/game.py) ---
st.markdown(
    """
    <div class="center-wrap">
      <form action="game">
        <button class="start-btn">🌱 Start Adventure</button>
      </form>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Waving bear (optional) ---
if bear_b64:
    st.markdown(f'<img class="waving-bear" src="data:image/png;base64,{bear_b64}" />',
                unsafe_allow_html=True)
else:
    st.info("Optional: add `waving_bear.png` next to `main.py` for the waving bear.")
