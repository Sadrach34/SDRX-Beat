"""
app.py – Main TUI application class for RofiBeats
Created by Sadrach Garcia (SDRX) on 2026-05-09

Layout (3 columns):
  LEFT   (28%) – Info canción + comentario
  CENTER (44%) – Lista numerada
  RIGHT  (28%) – Miniatura (personalizable por estación)

ESC → menú popup: Reanudar / Opciones / Salir

Keybindings:
  ENTER      Reproducir seleccionado / abrir playlist
  SPACE      Pausa / Play
  ← →        Seek ±5s
  Ctrl+←     Track anterior
  Ctrl+→     Track siguiente
  Ctrl+T     Buscar en lista actual
  b / BS     Volver a estaciones (desde playlist)
  s          Aleatorio
  d          Descargar (yt-dlp)
  o          Cambiar a Online
  l          Cambiar a Local
  r          Refrescar lista local
  a          Agregar estación online
  t          Renombrar estación (modo online)
  x          Eliminar estación (modo online)
  i          Cambiar miniatura (modo online)
  c          Editar comentario del item seleccionado
  ESC        Abrir menú
  q          Salir
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
import userdata
from config import (
    SUPPORTED_EXT,
    KEY_CTRL_RIGHT, KEY_CTRL_LEFT, KEY_CTRL_T,
)

MODE_ONLINE   = "online"
MODE_LOCAL    = "local"
MODE_PLAYLIST = "playlist"


class App:
    def __init__(self, stdscr):
        self.s    = stdscr
        self.mode = MODE_ONLINE

        # Online stations (from userdata.json)
        self._stations: list = []
        self.on_names:  list = []
        self.on_urls:   dict = {}
        self.on_thumbs: dict = {}
        self._reload_stations()

        # Playlist view
        self._pl_name     = ""
        self._pl_url      = ""
        self._pl_tracks   = []
        self._pl_fetching = False

        # Local music
        self._lock     = threading.Lock()
        self.loc_files = []
        self.loc_names = []

        # Per-mode cursor/scroll
        self._nav = {
            MODE_ONLINE:   {"cursor": 0, "scroll": 0},
            MODE_LOCAL:    {"cursor": 0, "scroll": 0},
            MODE_PLAYLIST: {"cursor": 0, "scroll": 0},
        }

        # Playback state
        self._np_title  = ""
        self._np_paused = False
        self._np_pos    = None
        self._np_dur    = None
        self._np_pl_pos = None

        # ESC menu
        self._menu_open     = False
        self._menu_selected = 0

        self._running = True
        self.status   = "  ↑↓ navegar · ENTER reproducir · ESC menú · q salir"

        draw.init_colors()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._load_local, daemon=True).start()

    # ── Station helpers ───────────────────────────────────────────────────────

    def _reload_stations(self):
        self._stations = userdata.get_stations()
        self.on_names  = [s["name"] for s in self._stations]
        self.on_urls   = {s["name"]: s["url"] for s in self._stations}
        self.on_thumbs = {s["name"]: s.get("thumbnail", "") for s in self._stations}

    # ── Cursor / scroll ───────────────────────────────────────────────────────

    @property
    def cursor(self): return self._nav[self.mode]["cursor"]
    @cursor.setter
    def cursor(self, v): self._nav[self.mode]["cursor"] = v

    @property
    def scroll(self): return self._nav[self.mode]["scroll"]
    @scroll.setter
    def scroll(self, v): self._nav[self.mode]["scroll"] = v

    # ── Background workers ────────────────────────────────────────────────────

    def _load_local(self):
        music_dir = userdata.get_music_dir()
        files = []
        for ext in SUPPORTED_EXT:
            files.extend(
                glob.glob(os.path.join(music_dir, "**", f"*{ext}"), recursive=True)
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
            self._pl_tracks = ["(yt-dlp not found)"]
        except subprocess.TimeoutExpired:
            self._pl_tracks = ["(timeout al cargar playlist)"]
        except Exception as e:
            self._pl_tracks = [f"(error: {e})"]
        finally:
            self._pl_fetching = False
            self.status = f"  🎶  {len(self._pl_tracks)} tracks cargados"

    # ── Session restore ───────────────────────────────────────────────────────

    def restore_session(self):
        if mpv.is_running():
            path = mpv.get("path") or ""
            if path.startswith("http") or path.startswith("ytdl"):
                saved = session.load()
                if saved and saved.get("type") == "online":
                    self._restore_online_ui(saved)
            else:
                self.mode = MODE_LOCAL
                self.status = "  🔗  Re-conectado a sesión mpv activa"
            return

        saved = session.load()
        if not saved:
            return
        kind = saved.get("type")

        if kind == "online":
            name = saved.get("station_name", "")
            url  = saved.get("url", "")
            idx  = saved.get("pl_index", 0)
            if url:
                mpv.play_online_at(url, idx)
                self._pl_name   = name
                self._pl_url    = url
                self._pl_tracks = []
                self._nav[MODE_PLAYLIST] = {"cursor": idx, "scroll": max(0, idx - 5)}
                self.mode   = MODE_PLAYLIST
                self.status = f"  ▶  Reanudado: {name} (track {idx + 1})"
                threading.Thread(target=self._fetch_playlist_tracks,
                                 args=(url,), daemon=True).start()

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
                self.status = f"  ▶  Reanudado track local {idx + 1}"

    def _restore_online_ui(self, saved: dict):
        name = saved.get("station_name", "")
        url  = saved.get("url", "")
        idx  = saved.get("pl_index", 0)
        self._pl_name   = name
        self._pl_url    = url
        self._pl_tracks = []
        self._nav[MODE_PLAYLIST] = {"cursor": idx, "scroll": max(0, idx - 5)}
        self.mode   = MODE_PLAYLIST
        self.status = f"  🔗  Re-conectado: {name}"
        threading.Thread(target=self._fetch_playlist_tracks,
                         args=(url,), daemon=True).start()

    def _drain_nav(self, nav_key: int):
        while True:
            k = self.s.getch()
            if k != nav_key:
                if k != -1:
                    curses.ungetch(k)
                break

    # ── List helpers ──────────────────────────────────────────────────────────

    def _cur_list(self) -> list:
        if self.mode == MODE_ONLINE:
            return list(self.on_names)
        if self.mode == MODE_PLAYLIST:
            return list(self._pl_tracks)
        with self._lock:
            return list(self.loc_names)

    def _clamp(self, lst: list):
        n = len(lst)
        self.cursor = 0 if n == 0 else max(0, min(self.cursor, n - 1))

    # ── Column geometry ───────────────────────────────────────────────────────

    def _cols(self, W: int):
        """Returns (left_w, left_x, center_w, center_x, right_w, right_x)."""
        left_w   = max(18, W * 28 // 100)
        right_w  = max(18, W * 28 // 100)
        center_w = max(10, W - left_w - right_w - 2)
        left_x   = 0
        center_x = left_w + 1
        right_x  = center_x + center_w + 1
        return left_w, left_x, center_w, center_x, right_w, right_x

    # ── Draw ──────────────────────────────────────────────────────────────────

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

        # Fixed row positions (bottom-up)
        hint_y   = H - 1
        prog_y   = H - 2
        np_y     = H - 3
        div_y    = H - 4
        status_y = H - 5
        col_top  = 1
        col_bot  = H - 6
        col_h    = max(0, col_bot - col_top + 1)

        # ── Header ────────────────────────────────────────────────────────────
        if self.mode == MODE_ONLINE:
            mode_lbl = "ONLINE STATIONS"
        elif self.mode == MODE_PLAYLIST:
            mode_lbl = f"PLAYLIST › {self._pl_name}"
        else:
            mode_lbl = "LOCAL MUSIC"
        hdr = f" 🎵 RofiBeats  [{mode_lbl}]"
        draw.fill_row(s, 0, W, draw.C_HDR())
        draw.safe_addstr(s, 0, 0, hdr[:W], draw.C_HDR())

        # ── Column geometry ───────────────────────────────────────────────────
        left_w, left_x, center_w, center_x, right_w, right_x = self._cols(W)

        # Vertical separators
        draw.vline(s, left_x + left_w, col_top, col_bot)
        draw.vline(s, right_x - 1,     col_top, col_bot)

        # ══ CENTER: numbered list ══════════════════════════════════════════════
        lst = self._cur_list()
        n   = len(lst)
        self._clamp(lst)

        list_label_row = col_top
        list_top       = col_top + 1
        list_rows      = max(0, col_h - 1)

        if n == 0:
            self.scroll = 0
        else:
            if self.cursor < self.scroll:
                self.scroll = self.cursor
            if self.cursor >= self.scroll + list_rows:
                self.scroll = self.cursor - list_rows + 1

        # Section label
        if self.mode == MODE_ONLINE:
            sec = f" 🌐 Estaciones ({n})"
        elif self.mode == MODE_PLAYLIST:
            sec = (" ⏳ Cargando…" if self._pl_fetching
                   else f" 🎶 {self._pl_name} ({n})")
        else:
            sec = f" 📁 Música Local ({n})"
        draw.safe_addstr(s, list_label_row, center_x,
                         sec[:center_w], draw.C_ACC())

        num_w = len(str(max(1, n)))
        for row in range(list_rows):
            idx = self.scroll + row
            if idx >= n:
                break
            name   = lst[idx]
            is_sel = (idx == self.cursor)
            is_now = (self.mode == MODE_PLAYLIST
                      and np_pl_pos is not None
                      and int(np_pl_pos) == idx)
            icon    = "▶" if is_sel else ("♪" if is_now else " ")
            num_str = f"{idx + 1:>{num_w}}."
            display = f" {num_str} {icon} {name}"[:center_w]
            row_y   = list_top + row
            if is_sel:
                draw.fill_row(s, row_y, center_w, draw.C_SEL(), center_x)
                draw.safe_addstr(s, row_y, center_x, display, draw.C_SEL())
            elif is_now:
                draw.safe_addstr(s, row_y, center_x, display, draw.C_GRN())
            else:
                draw.safe_addstr(s, row_y, center_x, display, draw.C_NRM())

        # ══ LEFT: info + comment panel ════════════════════════════════════════
        self._draw_info_panel(s, col_top, left_x, left_w, col_h,
                              np_title, np_paused, np_pos, np_dur, playing,
                              lst, n)

        # ══ RIGHT: thumbnail panel ════════════════════════════════════════════
        self._draw_thumb_panel(s, col_top, right_x, right_w, col_h, lst, n)

        # ── Status row ────────────────────────────────────────────────────────
        draw.safe_addstr(s, status_y, 1, self.status[:W - 2], draw.C_YLW())

        # ── Divider ───────────────────────────────────────────────────────────
        draw.safe_addstr(s, div_y, 0, "─" * W, draw.C_ACC())

        # ── Now-playing bar ───────────────────────────────────────────────────
        icon    = "⏸" if np_paused else ("▶" if playing else "■")
        np_text = f" {icon}  {np_title or 'Nada reproduciéndose'} "
        np_attr = draw.C_NPB() if (playing and not np_paused) else draw.C_YLW()
        draw.fill_row(s, np_y, W, np_attr)
        draw.safe_addstr(s, np_y, 0, np_text[:W], np_attr)

        # ── Progress bar ──────────────────────────────────────────────────────
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

        # ── Footer hints ──────────────────────────────────────────────────────
        if self.mode == MODE_PLAYLIST:
            hints = " SPC:pausa  ←→:seek  ^←:prev  ^→:next  ^T:buscar  d:dl  b:atrás  s:aleatorio  c:comentario  ESC:menú"
        elif self.mode == MODE_LOCAL:
            hints = " SPC:pausa  ←→:seek  ^←:prev  ^→:next  ^T:buscar  d:dl  o:online  s:aleatorio  c:comentario  ESC:menú"
        else:
            hints = " SPC:pausa  ^T:buscar  a:agregar  t:renombrar  x:eliminar  i:miniatura  c:comentario  ESC:menú"
        draw.fill_row(s, hint_y, W, draw.C_FTR())
        draw.safe_addstr(s, hint_y, 0, hints[:W].ljust(W), draw.C_FTR())

        s.refresh()

        # ESC menu painted on top if open
        if self._menu_open:
            draw.draw_esc_menu(s, self._menu_selected)

    # ── Left panel ────────────────────────────────────────────────────────────

    def _draw_info_panel(self, s, y0, x0, w, h,
                         np_title, np_paused, np_pos, np_dur, playing,
                         lst, n):
        iw = max(1, w - 1)          # inner width (leave 1 for separator)
        row = [y0]                   # mutable counter

        def put(text, attr=None):
            if row[0] >= y0 + h:
                return
            draw.safe_addstr(s, row[0], x0, text[:iw], attr or draw.C_NRM())
            row[0] += 1

        def div():
            put("─" * iw, draw.C_BDR())

        # Panel header
        put(" ℹ INFO ".center(iw), draw.C_ACC())

        # Now-playing
        if playing:
            icon = "⏸" if np_paused else "▶"
            put(f" {icon} {np_title or '...'}"[:iw], draw.C_GRN())
            put(f"   {draw.fmt_time(np_pos)} / {draw.fmt_time(np_dur)}", draw.C_YLW())
        else:
            put(" ■ Nada reproduciéndose", draw.C_YLW())

        div()

        # Selected item
        if n > 0:
            idx      = max(0, min(self.cursor, n - 1))
            sel_name = lst[idx]
            put(" Seleccionado:", draw.C_ACC())
            # Wrap name
            remaining = sel_name
            while remaining and row[0] < y0 + h - 4:
                put("  " + remaining[:iw - 2])
                remaining = remaining[iw - 2:]

            # URL (online only)
            if self.mode == MODE_ONLINE and idx < len(self.on_names):
                url = self.on_urls.get(self.on_names[idx], "")
                if url:
                    div()
                    put(" URL:", draw.C_ACC())
                    u = url
                    while u and row[0] < y0 + h - 3:
                        put("  " + u[:iw - 2])
                        u = u[iw - 2:]

            # Comment
            div()
            comment = userdata.get_comment(sel_name)
            put(" 💬 Comentario:", draw.C_ACC())
            if comment:
                c = comment
                while c and row[0] < y0 + h - 2:
                    put("  " + c[:iw - 2], draw.C_YLW())
                    c = c[iw - 2:]
            else:
                put("  (ninguno — pulsa c)", draw.C_NRM())

        # Bottom hint
        while row[0] < y0 + h - 1:
            put("")
        put(" c:comentar  ESC:menú"[:iw], draw.C_FTR())

    # ── Right panel ───────────────────────────────────────────────────────────

    def _draw_thumb_panel(self, s, y0, x0, w, h, lst, n):
        iw = max(1, w - 1)
        draw.safe_addstr(s, y0, x0, " 🖼 VISTA ".center(iw)[:iw], draw.C_ACC())

        thumb_y    = y0 + 1
        thumb_h    = max(1, h - 1)
        thumb_mode = userdata.get_thumbnail_mode()

        if thumb_mode == "none":
            draw.safe_addstr(s, thumb_y, x0, " [miniatura: off]"[:iw], draw.C_NRM())
            return

        label     = ""
        thumb_src = ""

        if self.mode == MODE_ONLINE and n > 0:
            idx       = max(0, min(self.cursor, n - 1))
            if idx < len(self.on_names):
                label     = self.on_names[idx]
                thumb_src = self.on_thumbs.get(label, "")
        elif self.mode == MODE_PLAYLIST:
            label     = self._pl_name
            thumb_src = self.on_thumbs.get(label, "")
        elif n > 0:
            idx   = max(0, min(self.cursor, n - 1))
            label = lst[idx]

        if thumb_src:
            try:
                lines = open(thumb_src).read().splitlines()
                draw.draw_thumbnail_block(s, thumb_y, x0, thumb_h, w, lines)
                return
            except Exception:
                pass

        draw.draw_thumbnail_placeholder(s, thumb_y, x0, thumb_h, w,
                                        label[:iw - 4] if label else "")

    # ── Handle input ──────────────────────────────────────────────────────────

    def handle(self, key) -> bool:
        if self._menu_open:
            return self._handle_menu(key)

        lst = self._cur_list()
        n   = len(lst)

        if key == ord('q'):
            return False

        elif key == 27:              # ESC → open menu
            self._menu_open     = True
            self._menu_selected = 0

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
                self.status = "  🌐  Estaciones Online"

        elif key == ord('\n'):
            self._play_selected()

        elif key == ord(' '):
            if mpv.is_running():
                mpv.toggle_pause()
                self.status = "  ⏸  Pausa/Reanudar"
            else:
                self._play_selected()

        elif key == curses.KEY_RIGHT:
            if mpv.is_running():
                mpv.seek(5)
                self.status = "  ⏩  +5s"

        elif key == curses.KEY_LEFT:
            if mpv.is_running():
                mpv.seek(-5)
                self.status = "  ⏪  -5s"

        elif key in KEY_CTRL_RIGHT:
            if mpv.is_running():
                mpv.next_track()
                self.status = "  ⏭  Siguiente"

        elif key in KEY_CTRL_LEFT:
            if mpv.is_running():
                mpv.prev_track()
                self.status = "  ⏮  Anterior"

        elif key == ord('s'):
            self._shuffle_current()

        elif key == ord('o'):
            self.mode   = MODE_ONLINE
            self.status = "  🌐  Estaciones Online"

        elif key == ord('l'):
            self.mode   = MODE_LOCAL
            self.status = "  📁  Música Local"

        elif key == ord('r'):
            threading.Thread(target=self._load_local, daemon=True).start()
            self.status = "  🔄  Actualizando lista local…"

        elif key == ord('d'):
            self._download_selected()

        elif key == ord('x'):
            self._remove_station_prompt()

        elif key == ord('a'):
            self._add_station_prompt()

        elif key == ord('t') and self.mode == MODE_ONLINE:
            self._rename_station_prompt()

        elif key == ord('i') and self.mode == MODE_ONLINE:
            self._set_thumbnail_prompt()

        elif key == ord('c'):
            self._edit_comment()

        elif key == KEY_CTRL_T:
            self._open_search()

        elif key > 0:
            self.status = f"  🔑  tecla={key}"

        return True

    def _handle_menu(self, key) -> bool:
        n = len(draw._MENU_ITEMS)
        if key in (27, ord('q')):
            self._menu_open = False
        elif key == curses.KEY_UP:
            self._menu_selected = (self._menu_selected - 1) % n
        elif key == curses.KEY_DOWN:
            self._menu_selected = (self._menu_selected + 1) % n
        elif key in (ord('\n'), curses.KEY_ENTER, ord(' ')):
            choice = self._menu_selected
            self._menu_open = False
            if choice == draw.MENU_RESUME:
                self.status = "  ▶  Reanudando…"
            elif choice == draw.MENU_OPTIONS:
                self._open_options_menu()
            elif choice == draw.MENU_QUIT:
                return False
        return True

    # ── Play selected ─────────────────────────────────────────────────────────

    def _play_selected(self):
        lst = self._cur_list()
        if not lst:
            self.status = "  ❌  Lista vacía"
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
            self.status = f"  ⏳  Cargando: {name}…"
            threading.Thread(target=self._fetch_playlist_tracks,
                             args=(url,), daemon=True).start()
            # Offer to save if not yet persisted
            saved_names = [s["name"] for s in userdata.get_stations()]
            if name not in saved_names:
                self._prompt_save_station(name, url)

        elif self.mode == MODE_PLAYLIST:
            mpv.jump_to(idx)
            self.status = f"  ▶  Track {idx + 1}"

        else:
            with self._lock:
                files = list(self.loc_files)
                names = list(self.loc_names)
            if not files:
                self.status = "  ❌  Sin archivos en ~/Music/"
                return
            mpv.play_local_ordered(files, idx)
            session.save_local(files, idx)
            self.status = f"  ▶  {names[idx]}"

    # ── Shuffle ───────────────────────────────────────────────────────────────

    def _shuffle_current(self):
        if self.mode in (MODE_LOCAL, MODE_PLAYLIST):
            with self._lock:
                files = list(self.loc_files)
                names = list(self.loc_names)
            if not files:
                self.status = "  ❌  Sin archivos para mezclar"
                return
            paired = list(zip(files, names))
            random.shuffle(paired)
            sf, sn = zip(*paired)
            sf, sn = list(sf), list(sn)
            mpv.play_local_ordered(sf, 0)
            with self._lock:
                self.loc_files = sf
                self.loc_names = sn
            session.save_local(sf, 0)
            self._nav[MODE_LOCAL] = {"cursor": 0, "scroll": 0}
            self.mode   = MODE_LOCAL
            self.status = "  🔀  Lista aleatoria"
        else:
            self.status = "  ❌  Selecciona una playlist primero"

    # ── Search ────────────────────────────────────────────────────────────────

    def _open_search(self):
        s = self.s
        H, W = s.getmaxyx()
        query  = ""
        prompt = " 🔍 Buscar: "
        s.nodelay(False)
        curses.curs_set(1)
        while True:
            s.nodelay(True); self.draw(); s.nodelay(False)
            bar = (prompt + query + " " * W)[:W]
            try:
                s.attron(draw.C_SEL())
                s.addstr(H - 5, 0, bar[:W])
                s.move(H - 5, min(len(prompt) + len(query), W - 1))
                s.attroff(draw.C_SEL())
            except curses.error:
                pass
            s.refresh()
            key = s.getch()
            if key == 27:
                break
            elif key in (ord('\n'), curses.KEY_ENTER):
                self._jump_to_match(query); break
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
                self.status = f"  🔍  #{i + 1}: {name[:50]}"
                return
        self.status = f"  ❌  Sin resultado para '{query}'"

    # ── Comment editor ────────────────────────────────────────────────────────

    def _edit_comment(self):
        lst = self._cur_list()
        if not lst:
            return
        idx = max(0, min(self.cursor, len(lst) - 1))
        key = lst[idx]
        cur = userdata.get_comment(key)
        new = self._inline_input("  💬 Comentario: ", prefill=cur)
        if new is None:
            self.status = "  ↩️  Cancelado"; return
        userdata.set_comment(key, new.strip())
        self.status = ("  ✅  Comentario guardado" if new.strip()
                       else "  🗑️  Comentario eliminado")

    # ── Options menu ──────────────────────────────────────────────────────────

    def _open_options_menu(self):
        s = self.s
        H, W = s.getmaxyx()
        thumb_mode = userdata.get_thumbnail_mode()
        music_dir  = userdata.get_music_dir()
        options = [
            ["Miniatura modo",  ["block", "ascii", "none"], thumb_mode],
            ["Directorio música", None, music_dir],
        ]
        sel = 0
        s.nodelay(False)

        while True:
            s.nodelay(True); self.draw(); s.nodelay(False)

            box_h = len(options) + 4
            box_w = min(W - 4, 54)
            y0    = max(0, (H - box_h) // 2)
            x0    = max(0, (W - box_w) // 2)

            for r in range(box_h):
                draw.safe_addstr(s, y0 + r, x0, " " * box_w, draw.C_NRM())
            draw.safe_addstr(s, y0,         x0, "╔" + "═" * (box_w - 2) + "╗", draw.C_BDR())
            draw.safe_addstr(s, y0+box_h-1, x0, "╚" + "═" * (box_w - 2) + "╝", draw.C_BDR())
            for r in range(1, box_h - 1):
                draw.safe_addstr(s, y0 + r, x0, "║", draw.C_BDR())
                draw.safe_addstr(s, y0 + r, x0 + box_w - 1, "║", draw.C_BDR())
            draw.safe_addstr(s, y0, x0 + (box_w - 10) // 2, " OPCIONES ", draw.C_HDR())

            for i, (label, choices, val) in enumerate(options):
                row  = y0 + 2 + i
                attr = draw.C_MNU() if i == sel else draw.C_NRM()
                text = f"  {label}: [{val}]" if choices else f"  {label}: {val}"
                draw.fill_row(s, row, box_w - 2, attr, x0 + 1)
                draw.safe_addstr(s, row, x0 + 1, text[:box_w - 2], attr)

            draw.safe_addstr(s, y0 + box_h - 2, x0 + 1,
                             "↑↓:mover  ENTER:editar  ESC:cerrar"[:box_w - 2],
                             draw.C_YLW())
            s.refresh()

            key = s.getch()
            if key == 27:
                break
            elif key == curses.KEY_UP:
                sel = (sel - 1) % len(options)
            elif key == curses.KEY_DOWN:
                sel = (sel + 1) % len(options)
            elif key in (ord('\n'), curses.KEY_ENTER):
                label, choices, val = options[sel]
                if choices:
                    nv = choices[(choices.index(val) + 1) % len(choices)]
                    options[sel][2] = nv
                    userdata.set_setting("thumbnail_mode", nv)
                    self.status = f"  ⚙  Miniatura: {nv}"
                else:
                    nv = self._inline_input(f"  {label}: ", prefill=val)
                    if nv:
                        options[sel][2] = nv
                        userdata.set_setting("music_dir", nv)
                        threading.Thread(target=self._load_local, daemon=True).start()
                        self.status = f"  ⚙  Dir. música: {nv}"
        s.nodelay(True)

    # ── Station CRUD prompts ──────────────────────────────────────────────────

    def _prompt_save_station(self, name: str, url: str):
        s = self.s; H, W = s.getmaxyx()
        msg = f"  💾 '{name[:38]}' — [Y] Guardar  [ESC] Ignorar"
        s.nodelay(False); curses.curs_set(0)
        while True:
            s.nodelay(True); self.draw(); s.nodelay(False)
            try:
                s.attron(draw.C_SEL())
                s.addstr(H - 5, 0, (msg + " " * W)[:W])
                s.attroff(draw.C_SEL())
            except curses.error:
                pass
            s.refresh()
            k = s.getch()
            if k in (ord('y'), ord('Y')):
                userdata.add_station(name, url)
                self._reload_stations()
                self.status = f"  ✅  Estación guardada: {name}"
            else:
                self.status = f"  ▶  {name}"
            break
        s.nodelay(True)

    def _add_station_prompt(self):
        if self.mode != MODE_ONLINE:
            self.status = "  ℹ️  Ve a Online Stations"; return
        url = self._inline_input("  ➕ URL: ")
        if not url:
            self.status = "  ↩️  Cancelado"; return
        url = url.strip()
        if not url.startswith("http"):
            self.status = "  ❌  URL inválida"; return
        name = self._inline_input("  🏷️  Nombre: ")
        if not name:
            self.status = "  ↩️  Cancelado"; return
        name = name.strip()
        if not userdata.add_station(name, url):
            self.status = f"  ⚠️  Ya existe '{name}'"; return
        self._reload_stations()
        self.cursor = len(self.on_names) - 1
        self.status = f"  ✅  Estación agregada: {name}"

    def _rename_station_prompt(self):
        if self.mode != MODE_ONLINE:
            self.status = "  ℹ️  Ve a Online Stations"; return
        lst = self._cur_list()
        if not lst: return
        idx      = max(0, min(self.cursor, len(lst) - 1))
        old_name = self.on_names[idx]
        new_name = self._inline_input("  ✏️  Nuevo nombre: ", prefill=old_name)
        if not new_name:
            self.status = "  ↩️  Cancelado"; return
        new_name = new_name.strip()
        if new_name == old_name:
            self.status = "  ℹ️  Sin cambios"; return
        if not userdata.rename_station(old_name, new_name):
            self.status = f"  ⚠️  '{new_name}' ya existe"; return
        self._reload_stations()
        self.status = f"  ✅  Renombrada → '{new_name}'"

    def _remove_station_prompt(self):
        if self.mode != MODE_ONLINE:
            self.status = "  ℹ️  Ve a Online Stations"; return
        lst = self._cur_list()
        if not lst: return
        idx  = max(0, min(self.cursor, len(lst) - 1))
        name = self.on_names[idx]
        s = self.s; H, W = s.getmaxyx()
        msg = f"  🗑️  ¿Eliminar '{name[:36]}'?  [Y] Sí  [ESC] No"
        s.nodelay(False)
        while True:
            s.nodelay(True); self.draw(); s.nodelay(False)
            try:
                s.attron(draw.C_SEL())
                s.addstr(H - 5, 0, (msg + " " * W)[:W])
                s.attroff(draw.C_SEL())
            except curses.error:
                pass
            s.refresh()
            k = s.getch()
            if k in (ord('y'), ord('Y')):
                userdata.remove_station(name)
                self._reload_stations()
                self.cursor = min(self.cursor, max(0, len(self.on_names) - 1))
                self.status = f"  🗑️  Eliminada: {name}"
            else:
                self.status = "  ↩️  Cancelado"
            break
        s.nodelay(True)

    def _set_thumbnail_prompt(self):
        if self.mode != MODE_ONLINE:
            self.status = "  ℹ️  Selecciona una estación"; return
        lst = self._cur_list()
        if not lst: return
        idx  = max(0, min(self.cursor, len(lst) - 1))
        name = self.on_names[idx]
        cur  = self.on_thumbs.get(name, "")
        path = self._inline_input("  🖼️  Ruta ASCII art (vacío=quitar): ", prefill=cur)
        if path is None:
            self.status = "  ↩️  Cancelado"; return
        userdata.set_station_thumbnail(name, path.strip())
        self._reload_stations()
        self.status = f"  ✅  Miniatura actualizada: '{name}'"

    # ── Download ──────────────────────────────────────────────────────────────

    def _download_selected(self):
        if self.mode == MODE_LOCAL:
            self.status = "  ℹ️  Ya está en disco"; return
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
            url = (r.get("data") if r and r.get("error") == "success" else self._pl_url)
        if not url:
            self.status = "  ❌  No se pudo obtener la URL"; return
        dest = userdata.get_music_dir()
        os.makedirs(dest, exist_ok=True)
        self.status = f"  ⬇️  Descargando: {label[:40]}…"
        def _do():
            try:
                subprocess.run(
                    ["yt-dlp", "-x", "--audio-format", "mp3",
                     "--audio-quality", "0",
                     "-o", os.path.join(dest, "%(title)s.%(ext)s"),
                     "--no-warnings", url],
                    capture_output=True)
                self.status = f"  ✅  Descargado: {label[:40]}"
                threading.Thread(target=self._load_local, daemon=True).start()
            except FileNotFoundError:
                self.status = "  ❌  yt-dlp no encontrado"
            except Exception as e:
                self.status = f"  ❌  {e}"
        threading.Thread(target=_do, daemon=True).start()

    # ── Generic inline text input ─────────────────────────────────────────────

    def _inline_input(self, prompt: str, prefill: str = "") -> "str | None":
        """Returns the entered text or None if ESC was pressed."""
        s = self.s
        H, W = s.getmaxyx()
        text    = prefill
        escaped = False
        s.nodelay(False); curses.curs_set(1)
        while True:
            s.nodelay(True); self.draw(); s.nodelay(False)
            bar = (prompt + text + " " * W)[:W]
            try:
                s.attron(draw.C_SEL())
                s.addstr(H - 5, 0, bar[:W])
                s.move(H - 5, min(len(prompt) + len(text), W - 1))
                s.attroff(draw.C_SEL())
            except curses.error:
                pass
            s.refresh()
            key = s.getch()
            if key == 27:
                escaped = True; break
            elif key in (ord('\n'), curses.KEY_ENTER):
                break
            elif key in (curses.KEY_BACKSPACE, 127):
                text = text[:-1]
            elif 32 <= key < 127:
                text += chr(key)
        curses.curs_set(0); s.nodelay(True)
        return None if escaped else text

    # ── Main loop ─────────────────────────────────────────────────────────────

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