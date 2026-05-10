"""
config.py – static configuration for RofiBeats TUI
Created by Sadrach Garcia (SDRX) on 2026-05-09
"""
import os

MUSIC_DIR     = os.path.expanduser("~/Music/")
MPV_SOCKET    = "/tmp/mpvsocket"
SESSION_FILE  = os.path.expanduser("~/.cache/rofibeats_session.json")
SUPPORTED_EXT = (".mp3", ".flac", ".wav", ".ogg", ".mp4", ".opus", ".m4a", ".aac")

ONLINE_STATIONS = [
    ("BackEnd Sadrach 🎸",
     "https://www.youtube.com/playlist?list=PLXuOK4h_ZtSbGV1FsT_nC0TRlf2EmwXEE"),
    ("Heavy Hitters Sadrach 🥊",
     "https://www.youtube.com/playlist?list=RDCLAK5uy_nVT2-bFfxplES7OQSLcnwlJqpsQ9gn0yY"),
    ("Radio - Lofi Girl 🎧",
     "https://play.streamafrica.net/lofiradio"),
    ("YT - Relaxing Piano 🎹",
     "https://youtu.be/6H7hXzjFoVU?si=nZTPREC9lnK1JJUG"),
    ("YT - Youtube Remix 📹",
     "https://youtube.com/playlist?list=PLeqTkIUlrZXlSNn3tcXAa-zbo95j0iN-0"),
    ("YT - Lofi Hip Hop Radio 📻",
     "https://www.youtube.com/live/jfKfPfyJRdk?si=PnJIA9ErQIAw6-qd"),
]

# Map station name → url for quick lookup
STATION_URL = {name: url for name, url in ONLINE_STATIONS}
STATION_NAMES = [name for name, _ in ONLINE_STATIONS]

# ── Keycodes ──────────────────────────────────────────────────────────────────
# Detected on user's terminal:
#   Ctrl+Right = 575
#   Ctrl+Left  = 539-545 range (confirmed working)
#   Ctrl+Down  = was firing prev (wrong) → exclude from prev set
#
# We define explicit sets so adding new terminals is easy.

KEY_CTRL_RIGHT = {575, 560, 561, 562, 563, 564, 565, 566, 567, 568}
KEY_CTRL_LEFT  = {539, 540, 541, 542, 543, 544, 545, 546, 547, 548}

# Ctrl+T = 20, Ctrl+S = 19
KEY_CTRL_T = 20
KEY_CTRL_S = 19
