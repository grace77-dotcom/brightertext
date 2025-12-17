import streamlit as st
import base64

# === Redirect if needed ===
params = st.query_params
if params.get("page", [None])[0] == "game":
    import pages.game
    st.stop()

# === Animated bear ===
def show_bear():
    with open("waving_bear.png", "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(f"""
        <style>
        .waving-bear {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            height: 120px;
            transform-origin: bottom left;
            animation: wave 1s ease-in-out infinite alternate;
            z-index: 9999;
        }}
        @keyframes wave {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(15deg); }}
        }}
        </style>
        <img src="data:image/png;base64,{encoded}" class="waving-bear" />
    """, unsafe_allow_html=True)

show_bear()

# === Background image ===
def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = get_base64_image("phonics_phorest.png")

# === Inject styles for full-screen background and remove Streamlit padding ===
st.markdown(
    f"""
    <style>
    /* Remove top padding and white bar */
    header {{ visibility: hidden; }}
    .block-container {{
        padding-top: 0rem;
        padding-bottom: 0rem;
    }}

    /* Set full-page background */
    .full-bg {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        z-index: -2;
    }}

    /* Button styling */
    .button-wrapper {{
    position: fixed;
    bottom: 700px;
    left: 1400px;
    width: auto;
    z-index: 9999;
    }}


    /* Transparent app */
    .stApp {{
        background: transparent;
        overflow: hidden;
    }}
    </style>
    <div class="full-bg"></div>
    <div class="button-wrapper">
    """,
    unsafe_allow_html=True
)

# === Button ===
st.markdown(
    f"""
    <style>
    .full-bg {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/png;base64,{bg_image}");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        z-index: -1;
    }}
    .start-button {{
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 9999;
    }}
    .stApp {{
        overflow: hidden;
    }}
    </style>

    <div class="full-bg"></div>
    <div class="start-button">
        <form action="?page=game">
            <button style="
                font-size:18px;
                padding:10px 20px;
                border-radius:10px;
                border:none;
                background-color:#ffffffcc;
                box-shadow:2px 2px 10px rgba(0,0,0,0.2);
                cursor:pointer;
            ">
                🌱 Start Adventure
            </button>
        </form>
    </div>
    """,
    unsafe_allow_html=True,
)
# === Close button wrapper div ===
st.markdown("</div>", unsafe_allow_html=True)

