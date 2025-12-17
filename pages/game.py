# pages/game.py

import os
import json
import base64
import random
from typing import Dict, List

import requests
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------
# BASIC CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Phonics Phorest – Game",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------
if "xp" not in st.session_state:
    st.session_state.xp = 0

if "level_thresholds" not in st.session_state:
    st.session_state.level_thresholds: Dict[int, int] = {
        1: 0,     # Constants
        2: 250,   # Short Vowels
        3: 500,   # Long Vowels
        4: 750,   # Tricky Sounds
        5: 1000,  # Rare Sounds
    }

if "current_level" not in st.session_state:
    st.session_state.current_level = 1

if "show_game" not in st.session_state:
    st.session_state.show_game = False  # False = level map

LEVEL_NAMES = {
    1: "Constants",
    2: "Short Vowels",
    3: "Long Vowels",
    4: "Tricky Sounds",
    5: "Rare Sounds",
}

# ---------------------------------------------------------------------
# PHONEME / GRAPHEME GROUPS BY LEVEL
# ---------------------------------------------------------------------
LEVEL_GRAPHEMES: Dict[int, List[str]] = {
    1: ["m", "s", "t", "n", "p", "b", "f", "d"],
    2: [
        "m", "s", "t", "n", "p", "b", "f", "d",
        "k", "g", "h", "ă", "ĕ", "ĭ", "ŏ", "ŭ",
    ],
    3: [
        "l", "r", "y", "w", "z",
        "ch", "sh", "th", "ng",
        "ā", "ē", "ī", "ō", "ū",
    ],
    4: [
        "ou", "oi", "ow",
        "ar", "or", "er", "ir", "ur",
        "j", "v", "ks",
    ],
    5: [
        "zh", "aw", "air", "ear", "ure", "al",
    ],
}

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def sync_xp_from_backend() -> int:
    """Read XP from FastAPI backend."""
    try:
        r = requests.get(f"{BACKEND_URL}/xp", timeout=2)
        r.raise_for_status()
        return int(r.json().get("xp", 0))
    except Exception:
        return st.session_state.xp


def get_max_unlocked_level() -> int:
    xp = st.session_state.xp
    thresholds = st.session_state.level_thresholds
    max_level = 1
    for lvl, need in thresholds.items():
        if xp >= need and lvl > max_level:
            max_level = lvl
    return max_level


def _first_existing(paths: List[str]):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _b64(path: str) -> str | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------
# BACKGROUND IMAGE (forest)
# ---------------------------------------------------------------------
BG_PATHS = ["phonics_phorest.png", "assets/phonics_phorest.png"]
BG_FILE = _first_existing(BG_PATHS)
BG_B64 = _b64(BG_FILE) if BG_FILE else None
BG_URL = f"data:image/png;base64,{BG_B64}" if BG_B64 else ""

if not BG_B64:
    st.warning(
        "Background image **phonics_phorest.png** not found. "
        "Put it next to `main.py` or in `assets/`."
    )

# ---------------------------------------------------------------------
# GLOBAL STYLING
# ---------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    header, footer {{visibility:hidden;}}
    .block-container {{
        padding: 0;
        margin: 0;
        max-width: 100%;
    }}
    .stApp {{
        background: #020617;
        color: #f9fafb;
    }}
    body {{
        background-image: url('{BG_URL}');
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}
    .level-overlay {{
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        background: rgba(15,23,42,0.9);
        border-radius: 28px;
        padding: 30px 34px 24px 34px;
        max-width: 1040px;
        margin: 30px auto;
        box-shadow: 0 24px 52px rgba(0,0,0,0.7);
        border: 1px solid rgba(148,163,184,0.85);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# SIDEBAR – XP DEBUG ONLY
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("Tutor Controls")
    st.caption("XP debug only (students won’t see this).")
    debug_xp = st.slider(
        "XP",
        0,
        1500,
        sync_xp_from_backend(),
        step=10,
        help="Use this to fake progress while testing.",
    )
    if debug_xp != st.session_state.xp:
        st.session_state.xp = debug_xp
        try:
            requests.post(f"{BACKEND_URL}/xp", json={"xp": int(debug_xp)}, timeout=2)
        except Exception:
            pass

# ---------------------------------------------------------------------
# SIMPLE CVC WORD BANK
# ---------------------------------------------------------------------
STATIC_CVC_WORDS = [
    "cat", "sat", "mat", "hat", "rat", "bat",
    "sun", "fun", "run",
    "sip", "sit", "sap", "set",
    "map", "man", "mop",
    "top", "tap", "tip",
    "log", "leg", "dig", "dog",
    "red", "bed",
    "pig", "big",
    "cup", "cap",
    "hen", "pen",
    "box", "fox",
    "jam", "ham",
]


def build_wordbank(gpc: str) -> List[str]:
    """3-letter word bank, biased to start with the grapheme when given."""
    base = STATIC_CVC_WORDS.copy()
    random.shuffle(base)

    g = (gpc or "").strip().lower()
    if not g:
        return base

    starts = [w for w in base if w.startswith(g)]
    contains = [w for w in base if g in w and not w.startswith(g)]
    others = [w for w in base if g not in w]

    weighted: List[str] = []
    weighted.extend(starts * 3)
    weighted.extend(contains * 2)
    weighted.extend(others)
    weighted = weighted or base
    random.shuffle(weighted)
    return weighted


def generate_rounds_for_level(level: int, n: int) -> List[Dict]:
    """Each round has: target, decoys, and a focus grapheme/phoneme label."""
    graphemes = LEVEL_GRAPHEMES.get(level, LEVEL_GRAPHEMES[1])
    rounds: List[Dict] = []

    for _ in range(n):
        gpc = random.choice(graphemes)
        bank = build_wordbank(gpc)
        if len(bank) < 3:
            bank = STATIC_CVC_WORDS.copy()
            random.shuffle(bank)

        random.shuffle(bank)
        target = bank[0]
        d1 = bank[1]
        d2 = bank[2]
        rounds.append({"target": target, "decoys": [d1, d2], "focus": gpc})

    return rounds


# ---------------------------------------------------------------------
# LEVEL SELECT SCREEN
# ---------------------------------------------------------------------
def level_card(level: int, xp: int, thresholds: Dict[int, int], unlocked: bool):
    need = thresholds[level]
    title = LEVEL_NAMES[level]
    status = "Unlocked" if unlocked else f"Locked · {need} XP"
    emoji = ["🍎", "🟡", "🌈", "🌀", "💫"][level - 1]
    badge_color = "#22c55e" if unlocked else "#6b7280"

    st.markdown(
        f"""
        <div style="
            border-radius: 22px;
            padding: 14px 16px;
            margin: 6px 2px;
            background: radial-gradient(circle at top left, #0f172a, #020617);
            border: 1px solid rgba(148,163,184,0.9);
            color: #e5e7eb;
            box-shadow: 0 14px 30px rgba(0,0,0,0.7);
        ">
          <div style="display:flex; align-items:center; justify-content:space-between;">
            <div style="font-size: 26px; font-weight: 800;">
              {emoji} {title}
            </div>
            <div style="
                font-size: 12px;
                padding: 5px 10px;
                border-radius: 999px;
                background:{badge_color};
                color:#020617;
                font-weight:700;
              ">
              Level {level}
            </div>
          </div>
          <div style="font-size: 14px; opacity:0.96; margin-top:6px;">
            {status}
          </div>
          <div style="font-size: 12px; opacity:0.85; margin-top:2px;">
            Sounds get a little trickier in each new level.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def level_select_screen():
    st.session_state.xp = sync_xp_from_backend()
    xp = st.session_state.xp
    thresholds = st.session_state.level_thresholds
    max_unlocked = get_max_unlocked_level()

    st.markdown(
        """
        <div class="level-overlay">
          <div style="text-align:center;">
            <h1 style="margin-bottom:6px; color:#f9fafb; font-size:32px;">
                🌲 Phonics Phorest: Sound Paths 🌲
            </h1>
            <p style="color:#cbd5ff; margin-top:0; font-size:15px;">
                Choose a glowing path stone. Earn apples ⭐ to unlock new sound worlds.
            </p>
          </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<p style='font-size:14px;'><b>Current XP:</b> "
        f"<code>{xp}</code></p>",
        unsafe_allow_html=True,
    )

    if max_unlocked < max(thresholds.keys()):
        next_level = max_unlocked + 1
        need = max(0, thresholds[next_level] - xp)
        st.caption(
            f"{need} more XP until **{LEVEL_NAMES[next_level]} "
            f"(Level {next_level})** unlocks."
        )
    else:
        st.caption("All levels unlocked — forest master 🌟")

    st.progress(min(xp / thresholds.get(5, 1000), 1.0))
    st.write("")

    rows = [[1, 2, 3], [4, 5]]
    for row in rows:
        cols = st.columns(len(row))
        for lvl, col in zip(row, cols):
            with col:
                unlocked = lvl <= max_unlocked
                btn_label = f"{'▶️' if unlocked else '🔒'} {LEVEL_NAMES[lvl]}"
                if st.button(
                    btn_label,
                    key=f"btn_lvl_{lvl}",
                    disabled=not unlocked,
                    use_container_width=True,
                ):
                    st.session_state.current_level = lvl
                    st.session_state.show_game = True
                    st.rerun()
                level_card(lvl, xp, thresholds, unlocked)

    st.caption(
        "Level 1 (Constants) is always open so every student can start their adventure."
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# SHOW LEVEL MAP OR GAME
# ---------------------------------------------------------------------
if not st.session_state.show_game:
    level_select_screen()
    st.stop()

# ---------------------------------------------------------------------
# IN-LEVEL HEADER
# ---------------------------------------------------------------------
top_cols = st.columns([1, 2, 1])
with top_cols[0]:
    if st.button("⬅️ Back to Level Map"):
        st.session_state.show_game = False
        st.rerun()

with top_cols[1]:
    st.markdown(
        f"<h3 style='text-align:center; color:#e5e7eb; font-size:24px;'>"
        f"{LEVEL_NAMES[st.session_state.current_level]} "
        f"(Level {st.session_state.current_level})</h3>",
        unsafe_allow_html=True,
    )

with top_cols[2]:
    st.markdown(
        f"<div style='text-align:right; color:#e5e7eb; font-size:14px;'>XP: "
        f"<b>{st.session_state.xp}</b></div>",
        unsafe_allow_html=True,
    )

current_level = st.session_state.current_level

# ---------------------------------------------------------------------
# BUILD ROUNDS FOR THIS LEVEL
# ---------------------------------------------------------------------
ROUNDS = generate_rounds_for_level(current_level, n=18)
ROUNDS_B64 = base64.b64encode(json.dumps(ROUNDS).encode("utf-8")).decode("utf-8")

# ---------------------------------------------------------------------
# APPLE GAME
# ---------------------------------------------------------------------
html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Phonics Phorest – Level {current_level}</title>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    overflow: hidden;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: transparent;
    height: 100%;
  }}
  #wrap {{
    position: relative;
    width: 100%;
    max-width: 1200px;
    height: 78vh;             /* fills most laptop screen */
    margin: 6px auto 0 auto;
    border-radius: 24px;
    overflow: hidden;
  }}
  #game {{
    display: block;
    width: 100%;
    height: 100%;
    background: transparent;
  }}
  #tap {{
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,.35);
    color: #fff;
    font-weight: 800;
    font-size: 20px;
    letter-spacing: .3px;
    text-align: center;
    padding: 14px;
  }}
  .hud {{
    position: absolute;
    left: 10px;
    bottom: 10px;
    background: #ffffffee;
    color: #1b4d2b;
    padding: 7px 11px;
    border-radius: 12px;
    font-weight: 800;
    font-size: 14px;
    box-shadow: 0 8px 18px rgba(0,0,0,.2);
  }}
  .toast {{
    position: absolute;
    right: 10px;
    top: 10px;
    background: #1b4d2b;
    color: #fff;
    padding: 6px 10px;
    border-radius: 12px;
    display: none;
    font-weight: 800;
    font-size: 13px;
  }}
  .overlay {{
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,.45);
    color: #fff;
    text-align: center;
    padding: 20px;
  }}
  .overlay.show {{ display: flex; }}
  .card {{
    background: rgba(20,20,20,.92);
    border: 1px solid rgba(255,255,255,.2);
    border-radius: 18px;
    padding: 18px 22px;
    max-width: 520px;
    font-size: 16px;
  }}
  .card button {{
    margin-top: 12px;
    padding: 8px 16px;
    border-radius: 10px;
    border: none;
    cursor: pointer;
    background: #4ade80;
    color: #0a0a0a;
    font-weight: 800;
    font-size: 15px;
  }}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="game"></canvas>
  <div id="tap">Click or tap to start (turns on sound)</div>
  <div class="hud">★ XP: <span id="xp">{st.session_state.xp}</span> · Move basket with ←/→ or A/D</div>
  <div class="toast" id="toast">+10 XP</div>
  <div id="pause" class="overlay">
    <div class="card">
      <div id="pauseText" style="line-height:1.45">
        Let's think about that word together.
      </div>
      <button id="resumeBtn">Try again</button>
    </div>
  </div>
</div>

<script>
  // ===== DATA FROM PYTHON =====
  const ROUNDS = JSON.parse(atob("{ROUNDS_B64}"));
  const BG_URL = {json.dumps(BG_URL)};
  const BACKEND_URL = {json.dumps(BACKEND_URL)};
  let XP = {st.session_state.xp};
  const LEVEL = {current_level};

  // ===== XP HUD + BACKEND SYNC =====
  const xpEl = document.getElementById("xp");
  const toastEl = document.getElementById("toast");

  function updateHUD() {{
    xpEl.textContent = XP;
  }}

  async function syncXP() {{
    try {{
      await fetch(BACKEND_URL + "/xp", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ xp: XP }})
      }});
    }} catch (e) {{
      console.warn("XP sync failed", e);
    }}
  }}

  function changeXP(amount, message) {{
    XP += amount;
    if (XP < 0) XP = 0;
    updateHUD();
    syncXP();
    toastEl.textContent = message;
    toastEl.style.display = "block";
    setTimeout(() => {{ toastEl.style.display = "none"; }}, 1000);
  }}

  updateHUD();

  // ===== CANVAS + FOREST BG =====
  const cvs = document.getElementById("game");
  const ctx = cvs.getContext("2d");

  function resize() {{
    const rect = document.getElementById("wrap").getBoundingClientRect();
    cvs.width = rect.width;
    cvs.height = rect.height;
  }}
  window.addEventListener("resize", resize);
  resize();

  let bgImg = null;
  if (BG_URL) {{
    bgImg = new Image();
    bgImg.src = BG_URL;
  }}

  function drawForestBG() {{
    const w = cvs.width, h = cvs.height;
    ctx.fillStyle = "#8fd19a";
    ctx.fillRect(0, 0, w, h);
    if (bgImg && bgImg.complete && bgImg.naturalWidth > 0) {{
      const iw = bgImg.naturalWidth, ih = bgImg.naturalHeight;
      const s = Math.max(w / iw, h / ih);
      const dw = Math.floor(iw * s), dh = Math.floor(ih * s);
      const dx = Math.floor((w - dw) / 2), dy = Math.floor((h - dh) / 2);
      ctx.drawImage(bgImg, dx, dy, dw, dh);
    }}
  }}

  // ===== BROWSER TTS =====
  let voice = null;
  function pickVoice() {{
    const synth = window.speechSynthesis;
    if (!synth) return null;
    const voices = synth.getVoices();
    if (!voices || !voices.length) return null;
    const prefs = voices.filter(v =>
      /Samantha|Allison|Joanna|en-US/i.test(v.name + " " + v.lang)
    );
    return prefs[0] || voices[0];
  }}

  function speak(text, onend) {{
    if (!window.speechSynthesis) {{
      if (onend) setTimeout(onend, 10);
      return;
    }}
    if (!voice) voice = pickVoice();
    const u = new SpeechSynthesisUtterance(text);
    if (voice) u.voice = voice;
    u.rate = 0.65;  // calm teacher pace
    u.pitch = 1.0;
    u.onend = () => onend && onend();
    window.speechSynthesis.speak(u);
  }}

  // ===== GAME STATE =====
  const LANES = [0.2, 0.5, 0.8];
  let basketLane = 1;
  const basketYRel = 0.88;

  let roundIdx = 0;
  let current = null;
  let currentMeta = null;

  let fallYRel = [-0.12, -0.12, -0.12];
  const fallSpeed = 0.16;  // a bit faster
  let announcing = true;
  let highlightLane = -1;
  let roundActive = false;
  let waitingForNext = false;

  const confetti = [];

  function laneX(i) {{ return Math.floor(cvs.width * LANES[i]); }}
  function relY(r) {{ return Math.floor(cvs.height * r); }}

  function drawApple(x, y, text, lane) {{
    const radius = Math.max(40, Math.floor(cvs.height * 0.10)); // BIG APPLES

    // highlight ring when reading
    if (highlightLane === lane) {{
      ctx.lineWidth = Math.max(4, Math.floor(radius * 0.22));
      ctx.strokeStyle = "rgba(255, 221, 0, 0.95)";
      ctx.beginPath();
      ctx.arc(x, y, radius + Math.floor(radius * 0.3), 0, Math.PI * 2);
      ctx.stroke();
    }}

    // apple body
    ctx.fillStyle = "#e11d48";
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // stem
    ctx.strokeStyle = "#4b5563";
    ctx.lineWidth = Math.max(3, Math.floor(radius * 0.08));
    ctx.beginPath();
    ctx.moveTo(x, y - radius * 0.9);
    ctx.lineTo(x, y - radius * 1.3);
    ctx.stroke();

    // leaf
    ctx.fillStyle = "#22c55e";
    ctx.beginPath();
    ctx.ellipse(
      x + radius * 0.55,
      y - radius * 1.0,
      radius * 0.45,
      radius * 0.25,
      -0.6,
      0,
      Math.PI * 2
    );
    ctx.fill();

    // word text
    ctx.fillStyle = "#fff";
    ctx.font = "bold " + Math.floor(radius * 0.9) + "px system-ui";
    ctx.textAlign = "center";
    ctx.fillText(text, x, y + Math.floor(radius * 0.2));
  }}

  function drawBasket() {{
    const w = Math.floor(cvs.width * 0.18);
    const h = Math.floor(cvs.height * 0.06);
    const x = laneX(basketLane) - Math.floor(w / 2);
    const y = relY(basketYRel);

    // basket base
    ctx.fillStyle = "#5d3a00";
    ctx.fillRect(x, y, w, h);

    // woven body
    const bodyH = Math.floor(h * 1.1);
    ctx.fillStyle = "#8b5a12";
    ctx.fillRect(
      x + Math.floor(w * 0.06),
      y - bodyH,
      Math.floor(w * 0.88),
      bodyH
    );

    // simple slats
    ctx.strokeStyle = "#a16207";
    ctx.lineWidth = 3;
    for (let i = 0; i < 4; i++) {{
      const sx = x + Math.floor(w * 0.12) + i * Math.floor(w * 0.16);
      ctx.beginPath();
      ctx.moveTo(sx, y - bodyH);
      ctx.lineTo(sx, y);
      ctx.stroke();
    }}

    return {{x, y, w, h}};
  }}

  function overlap(ax, ay, aw, ah, bx, by, bw, bh) {{
    return !(
      bx > ax + aw ||
      bx + bw < ax ||
      by > ay + ah ||
      by + bh < ay
    );
  }}

  function spawnConfetti(x, y) {{
    const colors = ["#f97316", "#22c55e", "#3b82f6", "#eab308", "#ec4899"];
    for (let i = 0; i < 90; i++) {{
      confetti.push({{
        x: x + (Math.random() - 0.5) * 40,
        y: y + (Math.random() - 0.5) * 20,
        vx: (Math.random() - 0.5) * 160,
        vy: -Math.random() * 240,
        size: 3 + Math.random() * 3,
        color: colors[Math.floor(Math.random() * colors.length)],
        life: 0,
        maxLife: 1.2 + Math.random() * 0.7
      }});
    }}
  }}

  // ===== ROUND LOGIC =====
  function buildCurrentFromMeta(meta) {{
    const words = [meta.target, meta.decoys[0], meta.decoys[1]];
    // shuffle words
    for (let i = words.length - 1; i > 0; i--) {{
      const j = Math.floor(Math.random() * (i + 1));
      [words[i], words[j]] = [words[j], words[i]];
    }}
    const correctLane = words.indexOf(meta.target);
    current = {{
      target: meta.target,
      words,
      correctLane,
      focus: meta.focus
    }};

    fallYRel = [-0.12, -0.12, -0.12];
    announcing = true;
    highlightLane = -1;
    roundActive = false;
  }}

  function startRound(newRound) {{
    if (newRound || !currentMeta) {{
      if (roundIdx >= ROUNDS.length) roundIdx = 0;
      currentMeta = ROUNDS[roundIdx++];
    }}
    buildCurrentFromMeta(currentMeta);

    const target = currentMeta.target;
    const words = current.words;

    // TTS sequence: instruct, then read each word twice.
    speak("Listen. You will hear three words. Catch the word " + target + ".", () => {{
      let idx = 0;
      function speakWordTwice() {{
        if (idx >= words.length) {{
          announcing = false;
          highlightLane = -1;
          roundActive = true;
          return;
        }}
        const w = words[idx];
        highlightLane = idx;
        speak(w, () => {{
          speak(w, () => {{
            highlightLane = -1;
            idx += 1;
            setTimeout(speakWordTwice, 120);  // small pause
          }});
        }});
      }}
      speakWordTwice();
    }});
  }}

  // ===== INPUT =====
  document.addEventListener("keydown", (e) => {{
    if (!roundActive) return;
    const k = e.key.toLowerCase();
    if (k === "arrowleft" || k === "a") {{
      basketLane = Math.max(0, basketLane - 1);
    }} else if (k === "arrowright" || k === "d") {{
      basketLane = Math.min(2, basketLane + 1);
    }}
  }});

  const resumeBtn = document.getElementById("resumeBtn");
  const pauseEl = document.getElementById("pause");
  const pauseText = document.getElementById("pauseText");

  resumeBtn.onclick = () => {{
    pauseEl.classList.remove("show");
    waitingForNext = false;
    startRound(false);   // retry same word
  }};

  const tap = document.getElementById("tap");
  tap.addEventListener("click", () => {{
    tap.style.display = "none";
    startRound(true);
    last = performance.now();
    requestAnimationFrame(tick);
  }});

  // ===== CONFETTI UPDATE =====
  function updateConfetti(dt) {{
    for (let i = confetti.length - 1; i >= 0; i--) {{
      const p = confetti[i];
      p.life += dt;
      if (p.life > p.maxLife) {{
        confetti.splice(i, 1);
        continue;
      }}
      p.vy += 340 * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
    }}
  }}

  function drawConfetti() {{
    confetti.forEach(p => {{
      const alpha = Math.max(0, 1 - p.life / p.maxLife);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = alpha;
      ctx.fillRect(p.x, p.y, p.size, p.size);
      ctx.globalAlpha = 1;
    }});
  }}

  // ===== MAIN LOOP =====
  let last = performance.now();

  function tick(ts) {{
    const dt = (ts - last) / 1000;
    last = ts;

    ctx.clearRect(0, 0, cvs.width, cvs.height);
    drawForestBG();

    if (!current) {{
      requestAnimationFrame(tick);
      return;
    }}

    // draw apples
    for (let i = 0; i < 3; i++) {{
      const y = announcing ? relY(0.22) : relY(fallYRel[i]);
      drawApple(laneX(i), y, current.words[i], i);
    }}

    const basket = drawBasket();

    if (roundActive && !announcing && !waitingForNext) {{
      for (let i = 0; i < 3; i++) {{
        fallYRel[i] += fallSpeed * dt;
      }}

      const radius = Math.max(40, Math.floor(cvs.height * 0.10));
      const aw = radius * 2;
      const ah = radius * 2;

      // check ALL apples vs basket
      for (let i = 0; i < 3; i++) {{
        const y = relY(fallYRel[i]);
        const ax = laneX(i) - radius;
        const ay = y - radius;
        const hit = overlap(ax, ay, aw, ah, basket.x, basket.y, basket.w, basket.h);
        if (hit) {{
          const clickedWord = current.words[i];
          const isCorrect = (i === current.correctLane);
          handleCatch(isCorrect, clickedWord);
          break;
        }}
      }}

      // if target falls past bottom → miss
      const targetY = relY(fallYRel[current.correctLane]);
      if (targetY - radius > cvs.height + 4) {{
        const targetWord = current.words[current.correctLane];
        handleCatch(false, "__miss__" + targetWord);
      }}
    }}

    updateConfetti(dt);
    drawConfetti();

    requestAnimationFrame(tick);
  }}

  function handleCatch(isCorrect, clickedWord) {{
    if (!roundActive || waitingForNext) return;
    roundActive = false;

    const word = current.target;
    const focus = current.focus || word[0];

    if (isCorrect) {{
      // CORRECT → praise + confetti + +10 XP + explain
      const cx = laneX(basketLane);
      const cy = relY(basketYRel);
      spawnConfetti(cx, cy);

      changeXP(10, "+10 XP 🎉");

      const msg =
        "Nice work! You caught " + word + ". " +
        "Listen: " + word + " starts with the " + focus + " sound.";

      waitingForNext = true;
      speak(word, () => {{
        speak(msg, () => {{
          setTimeout(() => {{
            waitingForNext = false;
            startRound(true);   // new word
          }}, 900);
        }});
      }});

    }} else {{
      // WRONG / MISSED → explain + -5 XP, retry same word
      changeXP(-5, "-5 XP · let's fix it");

      let caught = "";
      if (clickedWord && !clickedWord.startsWith("__miss__")) {{
        caught = clickedWord;
      }} else if (clickedWord && clickedWord.startsWith("__miss__")) {{
        caught = ""; // they missed everything
      }}

      let explain;
      if (caught) {{
        explain =
          "You caught " + caught + ". " +
          "But the target word was " + word + ". " +
          "Listen for the " + focus + " sound at the start of " + word + ".";
      }} else {{
        explain =
          "The word was " + word + ". " +
          "You can listen again for the " + focus + " sound.";
      }}

      pauseText.textContent = explain;
      waitingForNext = true;
      const overlay = document.getElementById("pause");
      overlay.classList.add("show");

      speak(word, () => {{
        speak(explain, null);
      }});
    }}
  }}
</script>
</body>
</html>
"""

components.html(html, height=650, scrolling=False)