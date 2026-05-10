"""
config.py – Static configuration for RofiBeats TUI
Created by Sadrach Garcia (SDRX) on 2026-05-09

Station data is now stored per-user in ~/.config/rofibeats/userdata.json
via the userdata module.  Only truly static constants remain here.
"""
import os

MPV_SOCKET    = "/tmp/mpvsocket"
MUSIC_DIR     = os.path.expanduser("~/Music")
SESSION_FILE  = os.path.expanduser("~/.cache/rofibeats_session.json")
SUPPORTED_EXT = (".mp3", ".flac", ".wav", ".ogg", ".mp4", ".opus", ".m4a", ".aac")

# ── Keycodes ──────────────────────────────────────────────────────────────────
KEY_CTRL_RIGHT = {575, 560, 561, 562, 563, 564, 565, 566, 567, 568}
KEY_CTRL_LEFT  = {539, 540, 541, 542, 543, 544, 545, 546, 547, 548}
KEY_CTRL_T     = 20
KEY_CTRL_S     = 19