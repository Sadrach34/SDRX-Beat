"""
mpv.py – MPV process management and IPC helpers
Created by Sadrach Garcia (SDRX) on 2026-05-09
"""
import os
import json
import socket
import subprocess

from config import MPV_SOCKET, MUSIC_DIR


def send(cmd: dict):
    """Send a JSON command to mpv's IPC socket. Returns parsed response or None."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(MPV_SOCKET)
            s.sendall((json.dumps(cmd) + "\n").encode())
            resp = s.recv(4096).decode()
            for line in resp.splitlines():
                try:
                    return json.loads(line)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def get(prop: str):
    """Get a property value from mpv. Returns the value or None."""
    r = send({"command": ["get_property", prop]})
    if r and r.get("error") == "success":
        return r.get("data")
    return None


def is_running() -> bool:
    return subprocess.run(["pgrep", "-x", "mpv"], capture_output=True).returncode == 0


def stop():
    subprocess.run(["pkill", "-x", "mpv"], capture_output=True)
    try:
        os.remove(MPV_SOCKET)
    except FileNotFoundError:
        pass


def toggle_pause():
    send({"command": ["cycle", "pause"]})


def next_track():
    send({"command": ["playlist-next"]})


def prev_track():
    send({"command": ["playlist-prev"]})


def seek(seconds: int):
    send({"command": ["seek", seconds]})


def jump_to(index: int):
    send({"command": ["set_property", "playlist-pos", index]})


def _find_mpris() -> str:
    candidates = [
        "/etc/mpv/scripts/mpris.so",
        "/etc/mpv/scripts/mpris.lua",
        "/usr/lib/mpv/scripts/mpris.so",
        "/usr/lib/mpv/scripts/mpris.lua",
        os.path.expanduser("~/.config/mpv/scripts/mpris.so"),
        os.path.expanduser("~/.config/mpv/scripts/mpris.lua"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""


def _base_cmd() -> list:
    cmd = [
        "mpv",
        f"--input-ipc-server={MPV_SOCKET}",
        "--vid=no",
        "--no-audio-display",
        "--audio-device=auto",
        "--ao=pipewire,pulse,alsa",
    ]
    mpris = _find_mpris()
    if mpris:
        cmd.append(f"--script={mpris}")
    return cmd


def play_local_ordered(files: list, start_index: int):
    """Play local file list in order starting at start_index."""
    if not files:
        return
    stop()
    cmd = _base_cmd() + [
        "--loop-playlist",
        f"--playlist-start={start_index}",
    ] + list(files)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def play_online(url: str):
    """Play an online station/playlist in default order."""
    stop()
    cmd = _base_cmd() + [
        "--loop-playlist",
        "--ytdl-raw-options=cookies-from-browser=firefox",
        "--ytdl-raw-options=extractor-args=youtube:player_client=android",
        (
            "--user-agent=Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36"
        ),
        url,
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def play_online_at(url: str, index: int):
    """Play an online playlist starting at a specific index."""
    stop()
    cmd = _base_cmd() + [
        "--loop-playlist",
        f"--playlist-start={index}",
        "--ytdl-raw-options=cookies-from-browser=firefox",
        "--ytdl-raw-options=extractor-args=youtube:player_client=android",
        (
            "--user-agent=Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36"
        ),
        url,
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
