"""
userdata.py – Per-user data store for RofiBeats TUI
Created by Sadrach Garcia (SDRX) on 2026-05-09

Persists to ~/.config/rofibeats/userdata.json:
{
  "stations": [
    { "name": "...", "url": "...", "thumbnail": "path/or/url/or/ascii" }
  ],
  "comments": {
    "Station or track name": "user comment text"
  },
  "settings": {
    "music_dir": "~/Music/",
    "thumbnail_mode": "ascii"      # "ascii" | "block" | "none"
  }
}
"""
import json
import os

_DATA_DIR  = os.path.expanduser("~/.config/rofibeats")
_DATA_FILE = os.path.join(_DATA_DIR, "userdata.json")

# ── Default stations (first-run seed) ─────────────────────────────────────────
_DEFAULT_STATIONS = [
    {"name": "BackEnd Sadrach 🎸",
     "url":  "https://www.youtube.com/playlist?list=PLXuOK4h_ZtSbGV1FsT_nC0TRlf2EmwXEE",
     "thumbnail": ""},
    {"name": "Heavy Hitters Sadrach 🥊",
     "url":  "https://www.youtube.com/playlist?list=RDCLAK5uy_nVT2-bFfxplES7OQSLcnwlJqpsQ9gn0yY",
     "thumbnail": ""},
    {"name": "Radio - Lofi Girl 🎧",
     "url":  "https://play.streamafrica.net/lofiradio",
     "thumbnail": ""},
    {"name": "YT - Relaxing Piano 🎹",
     "url":  "https://youtu.be/6H7hXzjFoVU?si=nZTPREC9lnK1JJUG",
     "thumbnail": ""},
    {"name": "YT - Youtube Remix 📹",
     "url":  "https://youtube.com/playlist?list=PLeqTkIUlrZXlSNn3tcXAa-zbo95j0iN-0",
     "thumbnail": ""},
    {"name": "YT - Lofi Hip Hop Radio 📻",
     "url":  "https://www.youtube.com/live/jfKfPfyJRdk?si=PnJIA9ErQIAw6-qd",
     "thumbnail": ""},
]

_DEFAULT_SETTINGS = {
    "music_dir":      "~/Music/",
    "thumbnail_mode": "block",   # "ascii" | "block" | "none"
}


# ── Internal load / save ───────────────────────────────────────────────────────

def _load_raw() -> dict:
    try:
        with open(_DATA_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_raw(data: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    try:
        with open(_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _data() -> dict:
    """Return the full userdata dict, seeding defaults on first run."""
    raw = _load_raw()
    changed = False

    if "stations" not in raw:
        raw["stations"] = list(_DEFAULT_STATIONS)
        changed = True
    if "comments" not in raw:
        raw["comments"] = {}
        changed = True
    if "settings" not in raw:
        raw["settings"] = dict(_DEFAULT_SETTINGS)
        changed = True
    else:
        for k, v in _DEFAULT_SETTINGS.items():
            if k not in raw["settings"]:
                raw["settings"][k] = v
                changed = True

    if changed:
        _save_raw(raw)
    return raw


# ── Public API ─────────────────────────────────────────────────────────────────

# --- Stations -----------------------------------------------------------------

def get_stations() -> list[dict]:
    """Return list of station dicts: [{name, url, thumbnail}, ...]"""
    return list(_data()["stations"])


def save_stations(stations: list[dict]):
    """Overwrite the full station list and persist."""
    raw = _data()
    raw["stations"] = list(stations)
    _save_raw(raw)


def add_station(name: str, url: str, thumbnail: str = "") -> bool:
    """Append a new station. Returns False if name already exists."""
    raw = _data()
    for s in raw["stations"]:
        if s["name"] == name:
            return False
    raw["stations"].append({"name": name, "url": url, "thumbnail": thumbnail})
    _save_raw(raw)
    return True


def remove_station(name: str) -> bool:
    """Remove station by name. Returns False if not found."""
    raw = _data()
    before = len(raw["stations"])
    raw["stations"] = [s for s in raw["stations"] if s["name"] != name]
    if len(raw["stations"]) == before:
        return False
    _save_raw(raw)
    return True


def rename_station(old_name: str, new_name: str) -> bool:
    """Rename a station in place. Returns False if old not found or new exists."""
    raw = _data()
    existing_names = {s["name"] for s in raw["stations"]}
    if old_name not in existing_names or new_name in existing_names:
        return False
    for s in raw["stations"]:
        if s["name"] == old_name:
            s["name"] = new_name
            break
    _save_raw(raw)
    return True


def set_station_thumbnail(name: str, thumbnail: str):
    """Set the thumbnail path/ASCII for a station."""
    raw = _data()
    for s in raw["stations"]:
        if s["name"] == name:
            s["thumbnail"] = thumbnail
            _save_raw(raw)
            return


# --- Comments -----------------------------------------------------------------

def get_comment(key: str) -> str:
    """Get the comment for a track/station key. Returns '' if none."""
    return _data()["comments"].get(key, "")


def set_comment(key: str, text: str):
    """Set or overwrite the comment for a track/station key."""
    raw = _data()
    if text:
        raw["comments"][key] = text
    else:
        raw["comments"].pop(key, None)
    _save_raw(raw)


def all_comments() -> dict:
    return dict(_data()["comments"])


# --- Settings -----------------------------------------------------------------

def get_setting(key: str, default=None):
    return _data()["settings"].get(key, default)


def set_setting(key: str, value):
    raw = _data()
    raw["settings"][key] = value
    _save_raw(raw)


def get_music_dir() -> str:
    return os.path.expanduser(get_setting("music_dir", "~/Music/"))


def get_thumbnail_mode() -> str:
    return get_setting("thumbnail_mode", "block")