"""
session.py – Save and restore playback state between runs.
Created by Sadrach Garcia (SDRX) on 2026-05-09

Saved to SESSION_FILE (JSON):
{
  "type":         "online" | "local",
  "url":          "...",          # online only
  "station_name": "...",          # online only
  "pl_index":     3,              # playlist position (online)
  "files":        [...],          # local only (full paths)
  "file_index":   7,              # local only
  "time_pos":     142.3           # seconds into track (best-effort)
}
"""
import json
import os

from config import SESSION_FILE
import mpv


def save():
    """Snapshot current mpv state to disk. Safe to call even if mpv is not running."""
    if not mpv.is_running():
        # nothing to save — but don't wipe an existing session either
        return

    data: dict = {}

    # Determine what's playing by inspecting mpv properties
    pl_count = mpv.get("playlist-count") or 0
    pl_pos   = mpv.get("playlist-pos")
    time_pos = mpv.get("time-pos")

    # Try to get the filename of the current entry to decide online vs local
    current_path = mpv.get("path") or mpv.get("filename") or ""

    is_online = current_path.startswith("http") or current_path.startswith("ytdl")

    if is_online:
        # We can't easily recover the original playlist URL from mpv alone,
        # so we rely on the caller passing metadata; we store what we can.
        # The App layer will call save_online() / save_local() directly.
        return

    # Local file session
    files = []
    for i in range(int(pl_count)):
        f = mpv.get(f"playlist/{i}/filename")
        if f:
            files.append(f)

    data = {
        "type":       "local",
        "files":      files,
        "file_index": int(pl_pos) if pl_pos is not None else 0,
        "time_pos":   float(time_pos) if time_pos is not None else 0.0,
    }
    _write(data)


def save_online(station_name: str, url: str):
    """Called by App when the user starts an online station."""
    pl_pos   = mpv.get("playlist-pos")
    time_pos = mpv.get("time-pos")
    data = {
        "type":         "online",
        "station_name": station_name,
        "url":          url,
        "pl_index":     int(pl_pos) if pl_pos is not None else 0,
        "time_pos":     float(time_pos) if time_pos is not None else 0.0,
    }
    _write(data)


def save_local(files: list, index: int):
    """Called by App when the user starts a local playlist."""
    time_pos = mpv.get("time-pos")
    data = {
        "type":       "local",
        "files":      list(files),
        "file_index": index,
        "time_pos":   float(time_pos) if time_pos is not None else 0.0,
    }
    _write(data)


def update_position():
    """
    Refresh pl_index and time_pos in the saved session without changing other fields.
    Called periodically by the poll thread.
    """
    if not mpv.is_running():
        return
    data = _read()
    if not data:
        return

    pl_pos   = mpv.get("playlist-pos")
    time_pos = mpv.get("time-pos")

    if pl_pos is not None:
        data["pl_index"]   = int(pl_pos)
        data["file_index"] = int(pl_pos)
    if time_pos is not None:
        data["time_pos"] = float(time_pos)

    _write(data)


def load() -> dict | None:
    """Return saved session dict or None if none exists."""
    return _read()


def clear():
    try:
        os.remove(SESSION_FILE)
    except FileNotFoundError:
        pass


# ── Internal ──────────────────────────────────────────────────────────────────

def _write(data: dict):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _read() -> dict | None:
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except Exception:
        return None
