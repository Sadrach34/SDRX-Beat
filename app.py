"""
app.py – Main TUI application class for RofiBeats
Created by Sadrach Garcia (SDRX) on 2026-05-09
"""
import curses
import os
import glob
import random
import subprocess
import threading
import time

import mpv
import session
import draw
from config import (
    MUSIC_DIR, SUPPORTED_EXT,
    STATION_NAMES, STATION_URL,
    KEY_CTRL_RIGHT, KEY_CTRL_LEFT, KEY_CTRL_T,
)

MODE_ONLINE   = "online"
MODE_LOCAL    = "local"
MODE_PLAYLIST = "playlist"


class App:
    def __init__(self, stdscr):
        self.s    = stdscr
        self.mode = MODE_ONLINE

        # Online
        self.on_names = list(STATION_NAMES)
        self.on_urls  = dict(STATION_URL)

        # Playlist view
        self._pl_name     = ""
        self._pl_url      = ""
        self._pl_tracks   = []
        self._pl_fetching = False

        # Local
        self._lock      = threading.Lock()
        self.loc_files  = []
        self.loc_names  = []

        # Per-mode cursor/scroll
        self._nav = {
            MODE_ONLINE:   {"cursor": 0, "scroll": 0},
            MODE_LOCAL:    {"cursor": 0, "scroll": 0},
            MODE_PLAYLIST: {"cursor": 0, "scroll": 0},
        }

        # Playback state (poll thread)
        self._np_title  = ""
        self._np_paused = False
        self._np_pos    = None
        self._np_dur    = None
        self._np_pl_pos = None

        self._running = True
        self.status   = "  Use ↑↓ to navigate · ENTER to play · q to quit"

        draw.init_colors()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._load_local, daemon=True).start()

    # ── cursor / scroll properties (per-mode) ─────────────────────────────────

    @property
    def cursor(self): return self._nav[self.mode]["cursor"]
    @cursor.setter
    def cursor(self, v): self._nav[self.mode]["cursor"] = v

    @property
    def scroll(self): return self._nav[self.mode]["scroll"]
    @scroll.setter
    def scroll(self, v): self._nav[self.mode]["scroll"] = v

    # ── background workers ────────────────────────────────────────────────────

    def _load_local(self):
        files = []
        for ext in SUPPORTED_EXT:
            files.extend(
                glob.glob(os.path.join(MUSIC_DIR, "**", f"*{ext}"), recursive=True)
            )
        files = sorted(files)
        names = [os.path.basename(f) for f in files]
        with self._lock:
            self.loc_files = files
            self.loc_names = names

    def _poll_loop(self):
        tick = 0
        while self._running:
            time.sleep(0.4)
            if mpv.is_running():
                title  = mpv.get("media-title") or mpv.get("filename") or ""
                paused = bool(mpv.get("pause"))
                pos    = mpv.get("time-pos")
                dur    = mpv.get("duration")
                pl_pos = mpv.get("playlist-pos")
            else:
                title, paused, pos, dur, pl_pos = "", False, None, None, None
            with self._lock:
                self._np_title  = title
                self._np_paused = paused
                self._np_pos    = pos
                self._np_dur    = dur
                self._np_pl_pos = pl_pos
            # Save session position every ~5s
            tick += 1
            if tick % 12 == 0:
                session.update_position()

    def _fetch_playlist_tracks(self, url: str):
        self._pl_fetching = True
        self._pl_tracks   = []
        try:
            r = subprocess.run(
                ["yt-dlp", "--flat-playlist", "--print", "title",
                 "--no-warnings", url],
                capture_output=True, text=True, timeout=60
            )
            lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
            self._pl_tracks = lines or ["(no tracks found)"]
        except FileNotFoundError:
            self._pl_tracks = ["(yt-dlp not found — sudo pacman -S yt-dlp)"]
        except subprocess.TimeoutExpired:
            self._pl_tracks = ["(timed out fetching playlist)"]
        except Exception as e:
            self._pl_tracks = [f"(error: {e})"]
        finally:
            self._pl_fetching = False
            self.status = f"  🎶  {len(self._pl_tracks)} tracks loaded"

    # ── session restore ───────────────────────────────────────────────────────

    def restore_session(self):
        """Called once at startup. If mpv is already running, just re-attach UI.
           If not running but a session exists, resume it."""
        if mpv.is_running():
            # Already playing — just show the current state in playlist view
            # Try to figure out what's playing
            path = mpv.get("path") or ""
            if path.startswith("http") or path.startswith("ytdl"):
                # Online — try to match to a known station
                saved = session.load()
                if saved and saved.get("type") == "online":
                    self._restore_online_ui(saved)
            else:
                self.mode = MODE_LOCAL
                self.status = "  🔗  Re-attached to running mpv session"
            return

        saved = session.load()
        if not saved:
            return

        kind = saved.get("type")

        if kind == "online":
            name  = saved.get("station_name", "")
            url   = saved.get("url", "")
            idx   = saved.get("pl_index", 0)
            if url:
                mpv.play_online_at(url, idx)
                self._pl_name   = name
                self._pl_url    = url
                self._pl_tracks = []
                self._nav[MODE_PLAYLIST] = {"cursor": idx, "scroll": max(0, idx - 5)}
                self.mode   = MODE_PLAYLIST
                self.status = f"  ▶  Resumed: {name} (track {idx + 1})"
                threading.Thread(
                    target=self._fetch_playlist_tracks,
                    args=(url,), daemon=True
                ).start()

        elif kind == "local":
            files = saved.get("files", [])
            idx   = saved.get("file_index", 0)
            if files:
                mpv.play_local_ordered(files, idx)
                with self._lock:
                    self.loc_files = files
                    self.loc_names = [os.path.basename(f) for f in files]
                self._nav[MODE_LOCAL] = {"cursor": idx, "scroll": max(0, idx - 5)}
                self.mode   = MODE_LOCAL
                self.status = f"  ▶  Resumed local track {idx + 1}"

        elif kind == "shuffle":
            mpv.play_local_shuffle()
            self.mode   = MODE_LOCAL
            self.status = "  🔀  Resumed shuffle"

    def _restore_online_ui(self, saved: dict):
        """Re-attach UI to a running online session without restarting mpv."""
        name = saved.get("station_name", "")
        url  = saved.get("url", "")
        idx  = saved.get("pl_index", 0)
        self._pl_name   = name
        self._pl_url    = url
        self._pl_tracks = []
        self._nav[MODE_PLAYLIST] = {"cursor": idx, "scroll": max(0, idx - 5)}
        self.mode   = MODE_PLAYLIST
        self.status = f"  🔗  Re-attached: {name}"
        threading.Thread(
            target=self._fetch_playlist_tracks,
            args=(url,), daemon=True
        ).start()

    def _drain_nav(self, nav_key: int):
        """Discard buffered repeats of nav_key; put back any different key."""
        while True:
            k = self.s.getch()
            if k != nav_key:
                if k != -1:
                    curses.ungetch(k)
                break

    # ── list helpers ──────────────────────────────────────────────────────────

    def _cur_list(self) -> list:
        if self.mode == MODE_ONLINE:
            return list(self.on_names)
        if self.mode == MODE_PLAYLIST:
            return list(self._pl_tracks)
        with self._lock:
            return list(self.loc_names)

    def _clamp(self, lst: list):
        n = len(lst)
        if n == 0:
            self.cursor = 0
        else:
            self.cursor = max(0, min(self.cursor, n - 1))

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self):
        s = self.s
        s.erase()
        H, W = s.getmaxyx()

        with self._lock:
            np_title  = self._np_title
            np_paused = self._np_paused
            np_pos    = self._np_pos
            np_dur    = self._np_dur
            np_pl_pos = self._np_pl_pos
        playing = mpv.is_running()

        # Layout (bottom-up):
        #  H-1  hints
        #  H-2  progress bar
        #  H-3  now-playing
        #  H-4  divider
        #  H-5  status
        #  0    header
        #  1..H-6  list (row 1 = section label, 2.. = items)
        hint_y   = H - 1
        prog_y   = H - 2
        np_y     = H - 3
        div_y    = H - 4
        status_y = H - 5
        list_top = 1
        list_bot = H - 6
        list_h   = max(0, list_bot - list_top + 1)
        content_top  = list_top + 1
        content_rows = max(0, list_h - 1)

        # ── header ────────────────────────────────────────────────────────────
        if self.mode == MODE_ONLINE:
            mode_lbl = "ONLINE STATIONS"
        elif self.mode == MODE_PLAYLIST:
            mode_lbl = f"PLAYLIST › {self._pl_name}"
        else:
            mode_lbl = "LOCAL MUSIC"
        hdr = f" 🎵 RofiBeats  [{mode_lbl}]"
        draw.fill_row(s, 0, W, draw.C_HDR())
        draw.safe_addstr(s, 0, 0, hdr[:W], draw.C_HDR())

        # ── list ──────────────────────────────────────────────────────────────
        lst = self._cur_list()
        n   = len(lst)
        self._clamp(lst)

        if n == 0:
            self.scroll = 0
        else:
            if self.cursor < self.scroll:
                self.scroll = self.cursor
            if self.cursor >= self.scroll + content_rows:
                self.scroll = self.cursor - content_rows + 1

        # section label
        if self.mode == MODE_ONLINE:
            sec = f"🌐 Online Stations  ({n} stations)"
        elif self.mode == MODE_PLAYLIST:
            sec = ("⏳ Loading playlist…" if self._pl_fetching
                   else f"🎶 {self._pl_name}  ({n} tracks)")
        else:
            sec = f"📁 Local Music  ({n} files)"
        draw.safe_addstr(s, list_top, 1, sec[:W - 2], draw.C_ACC())

        # items
        for row in range(content_rows):
            idx    = self.scroll + row
            if idx >= n:
                break
            name   = lst[idx]
            is_sel = (idx == self.cursor)
            is_now = (
                self.mode == MODE_PLAYLIST
                and np_pl_pos is not None
                and int(np_pl_pos) == idx
            )
            prefix  = "▶ " if is_sel else ("♪ " if is_now else "  ")
            display = (prefix + name)[:W - 2]
            row_y   = content_top + row
            if is_sel:
                draw.fill_row(s, row_y, W, draw.C_SEL())
                draw.safe_addstr(s, row_y, 1, display, draw.C_SEL())
            elif is_now:
                draw.safe_addstr(s, row_y, 1, display, draw.C_GRN())
            else:
                draw.safe_addstr(s, row_y, 1, display, draw.C_NRM())

        # ── status ────────────────────────────────────────────────────────────
        draw.safe_addstr(s, status_y, 1, self.status[:W - 2], draw.C_YLW())

        # ── divider ───────────────────────────────────────────────────────────
        draw.safe_addstr(s, div_y, 0, "─" * W, draw.C_ACC())

        # ── now-playing bar ───────────────────────────────────────────────────
        icon    = "⏸" if np_paused else ("▶" if playing else "■")
        np_text = f" {icon}  {np_title or 'Nothing playing'} "
        np_attr = draw.C_NPB() if (playing and not np_paused) else draw.C_YLW()
        draw.fill_row(s, np_y, W, np_attr)
        draw.safe_addstr(s, np_y, 0, np_text[:W], np_attr)

        # ── progress bar ──────────────────────────────────────────────────────
        frac = 0.0
        if playing and np_pos is not None and np_dur:
            try:
                frac = float(np_pos) / float(np_dur)
            except Exception:
                pass
        time_str = f" {draw.fmt_time(np_pos)} / {draw.fmt_time(np_dur)} "
        draw.safe_addstr(s, prog_y, 0, time_str, draw.C_ACC())
        bar_x = len(time_str)
        bar_w = max(4, W - bar_x - 1)
        draw.progress_bar(s, prog_y, bar_x, bar_w, frac)

        # ── hints ─────────────────────────────────────────────────────────────
        if self.mode == MODE_PLAYLIST:
            hints = " SPC:pause  ←→:seek  ^←:prev  ^→:next  ^T:search  d:dl  BS:back  s:shuffle  q:quit"
        elif self.mode == MODE_LOCAL:
            hints = " SPC:pause  ←→:seek  ^←:prev  ^→:next  ^T:search  d:dl  o:online  s:shuffle  q:quit"
        else:
            hints = " SPC:pause  ←→:seek  ^←:prev  ^→:next  ^T:search  o:online  l:local  s:shuffle  q:quit"
        draw.fill_row(s, hint_y, W, draw.C_FTR())
        draw.safe_addstr(s, hint_y, 0, hints[:W].ljust(W), draw.C_FTR())

        s.refresh()

    # ── input ─────────────────────────────────────────────────────────────────

    def handle(self, key) -> bool:
        lst = self._cur_list()
        n   = len(lst)

        if key in (ord('q'), 27):
            return False

        elif key == curses.KEY_UP:
            if n: self.cursor = (self.cursor - 1) % n
            self._drain_nav(key)

        elif key == curses.KEY_DOWN:
            if n: self.cursor = (self.cursor + 1) % n
            self._drain_nav(key)

        elif key == curses.KEY_PPAGE:
            self.cursor = max(0, self.cursor - 10)
            self._drain_nav(key)

        elif key == curses.KEY_NPAGE:
            self.cursor = min(max(0, n - 1), self.cursor + 10)
            self._drain_nav(key)

        elif key in (curses.KEY_BACKSPACE, 127, ord('b')):
            if self.mode == MODE_PLAYLIST:
                self.mode = MODE_ONLINE
                self.status = "  🌐  Online Stations"

        elif key == ord('\n'):
            self._play_selected()

        elif key == ord(' '):
            if mpv.is_running():
                mpv.toggle_pause()
                self.status = "  ⏸  Toggled pause"
            else:
                self._play_selected()

        # ── seek with plain arrows ─────────────────────────────────────────────
        elif key == curses.KEY_RIGHT:
            if mpv.is_running():
                mpv.seek(5)
                self.status = "  ⏩  +5s"

        elif key == curses.KEY_LEFT:
            if mpv.is_running():
                mpv.seek(-5)
                self.status = "  ⏪  -5s"

        # ── Ctrl+Right → next track ───────────────────────────────────────────
        elif key in KEY_CTRL_RIGHT:
            if mpv.is_running():
                mpv.next_track()
                self.status = "  ⏭  Next track"

        # ── Ctrl+Left → previous track ────────────────────────────────────────
        elif key in KEY_CTRL_LEFT:
            if mpv.is_running():
                mpv.prev_track()
                self.status = "  ⏮  Previous track"

        elif key == ord('s'):
            self._shuffle_current()

        elif key == ord('o'):
            self.mode   = MODE_ONLINE
            self.status = "  🌐  Online Stations"

        elif key == ord('l'):
            self.mode   = MODE_LOCAL
            self.status = "  📁  Local Music"

        elif key == ord('r'):
            threading.Thread(target=self._load_local, daemon=True).start()
            self.status = "  🔄  Refreshing local list…"

        elif key == ord('d'):
            self._download_selected()

        elif key == KEY_CTRL_T:
            self._open_search()

        elif key > 0:
            self.status = f"  🔑  key={key}  (unrecognised)"

        return True

    # ── play selected ─────────────────────────────────────────────────────────

    def _play_selected(self):
        lst = self._cur_list()
        if not lst:
            self.status = "  ❌  List is empty"
            return
        idx = max(0, min(self.cursor, len(lst) - 1))

        if self.mode == MODE_ONLINE:
            name = self.on_names[idx]
            url  = self.on_urls[name]
            mpv.play_online(url)
            session.save_online(name, url)
            self._pl_name     = name
            self._pl_url      = url
            self._pl_tracks   = []
            self._nav[MODE_PLAYLIST] = {"cursor": 0, "scroll": 0}
            self.mode   = MODE_PLAYLIST
            self.status = f"  ⏳  Loading playlist: {name}…"
            threading.Thread(
                target=self._fetch_playlist_tracks,
                args=(url,), daemon=True
            ).start()

        elif self.mode == MODE_PLAYLIST:
            mpv.jump_to(idx)
            self.status = f"  ▶  Track {idx + 1}"

        else:  # local
            with self._lock:
                files = list(self.loc_files)
                names = list(self.loc_names)
            if not files:
                self.status = "  ❌  No local files found in ~/Music/"
                return
            mpv.play_local_ordered(files, idx)
            session.save_local(files, idx)
            self.status = f"  ▶  {names[idx]}"

    # ── shuffle current playlist ──────────────────────────────────────────────

    def _shuffle_current(self):
        if self.mode in (MODE_LOCAL, MODE_PLAYLIST):
            with self._lock:
                files = list(self.loc_files)
                names = list(self.loc_names)
            if not files:
                self.status = "  ❌  No local files to shuffle"
                return
            paired = list(zip(files, names))
            random.shuffle(paired)
            shuffled_files, shuffled_names = zip(*paired)
            shuffled_files = list(shuffled_files)
            shuffled_names = list(shuffled_names)
            mpv.play_local_ordered(shuffled_files, 0)
            with self._lock:
                self.loc_files = shuffled_files
                self.loc_names = shuffled_names
            session.save_local(shuffled_files, 0)
            self._nav[MODE_LOCAL] = {"cursor": 0, "scroll": 0}
            self.mode   = MODE_LOCAL
            self.status = "  🔀  Shuffled playlist"
        elif self.mode == MODE_ONLINE:
            self.status = "  ❌  Select a playlist first"

    # ── search ────────────────────────────────────────────────────────────────

    def _open_search(self):
        s = self.s
        H, W = s.getmaxyx()
        query = ""
        s.nodelay(False)
        curses.curs_set(1)
        prompt = " 🔍 Search: "

        while True:
            # redraw background
            s.nodelay(True)
            self.draw()
            s.nodelay(False)

            # draw search bar over status row
            status_y = H - 5
            bar = (prompt + query + " " * W)[:W]
            try:
                s.attron(draw.C_SEL())
                s.addstr(status_y, 0, bar[:W])
                s.move(status_y, min(len(prompt) + len(query), W - 1))
                s.attroff(draw.C_SEL())
            except curses.error:
                pass
            s.refresh()

            key = s.getch()

            if key == 27:
                break
            elif key in (ord('\n'), curses.KEY_ENTER):
                self._jump_to_match(query)
                break
            elif key in (curses.KEY_BACKSPACE, 127):
                query = query[:-1]
            elif 32 <= key < 127:
                query += chr(key)

            if query:
                self._jump_to_match(query)

        curses.curs_set(0)
        s.nodelay(True)

    def _jump_to_match(self, query: str):
        lst = self._cur_list()
        q   = query.lower()
        for i, name in enumerate(lst):
            if q in name.lower():
                self.cursor = i
                self.status = f"  🔍  Match #{i + 1}: {name[:50]}"
                return
        self.status = f"  ❌  No match for '{query}'"

    # ── download ──────────────────────────────────────────────────────────────

    def _download_selected(self):
        if self.mode == MODE_LOCAL:
            self.status = "  ℹ️  Already on disk"
            return

        url, label = None, ""

        if self.mode == MODE_ONLINE:
            lst = self._cur_list()
            if not lst: return
            idx   = max(0, min(self.cursor, len(lst) - 1))
            label = self.on_names[idx]
            url   = self.on_urls[label]

        elif self.mode == MODE_PLAYLIST:
            lst = self._cur_list()
            if not lst: return
            idx   = max(0, min(self.cursor, len(lst) - 1))
            label = lst[idx]
            r = mpv.send({"command": ["get_property", f"playlist/{idx}/filename"]})
            if r and r.get("error") == "success":
                url = r.get("data")
            else:
                url = self._pl_url

        if not url:
            self.status = "  ❌  Could not get URL"
            return

        dest = os.path.expanduser("~/Music/")
        os.makedirs(dest, exist_ok=True)
        self.status = f"  ⬇️  Downloading: {label[:40]}…"

        def _do():
            try:
                subprocess.run(
                    ["yt-dlp", "-x", "--audio-format", "mp3",
                     "--audio-quality", "0",
                     "-o", os.path.join(dest, "%(title)s.%(ext)s"),
                     "--no-warnings", url],
                    capture_output=True
                )
                self.status = f"  ✅  Downloaded: {label[:40]}"
                threading.Thread(target=self._load_local, daemon=True).start()
            except FileNotFoundError:
                self.status = "  ❌  yt-dlp not found (sudo pacman -S yt-dlp)"
            except Exception as e:
                self.status = f"  ❌  {e}"

        threading.Thread(target=_do, daemon=True).start()

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self):
        curses.curs_set(0)
        self.s.keypad(True)
        self.s.nodelay(True)

        self.restore_session()

        while True:
            self.draw()
            try:
                key = self.s.getch()
            except curses.error:
                key = -1
            if key != -1 and not self.handle(key):
                break
            time.sleep(0.05)

        self._running = False
