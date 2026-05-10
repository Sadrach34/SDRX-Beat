"""
draw.py – curses drawing helpers for RofiBeats TUI
Created by Sadrach Garcia (SDRX) on 2026-05-09
"""
import curses
import time


def splash_screen(stdscr, logo_path: str):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    stdscr.erase()
    H, W = stdscr.getmaxyx()
    try:
        with open(logo_path) as f:
            lines = f.read().splitlines()
    except Exception:
        lines = ["SDRX"]
    start_y = max(0, (H - len(lines)) // 2)
    attr = curses.color_pair(2) | curses.A_BOLD
    for i, line in enumerate(lines):
        x = max(0, (W - len(line)) // 2)
        try:
            stdscr.addstr(start_y + i, x, line[:W], attr)
        except curses.error:
            pass
    stdscr.refresh()
    time.sleep(2)


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN,   -1)
    curses.init_pair(3, curses.COLOR_WHITE,  -1)
    curses.init_pair(4, curses.COLOR_GREEN,  -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)
    curses.init_pair(6, curses.COLOR_BLACK,  curses.COLOR_GREEN)
    curses.init_pair(7, curses.COLOR_WHITE,  curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(9, curses.COLOR_CYAN,   curses.COLOR_BLACK)


def C_HDR():  return curses.color_pair(1) | curses.A_BOLD
def C_ACC():  return curses.color_pair(2) | curses.A_BOLD
def C_NRM():  return curses.color_pair(3)
def C_SEL():  return curses.color_pair(1) | curses.A_BOLD
def C_GRN():  return curses.color_pair(4) | curses.A_BOLD
def C_YLW():  return curses.color_pair(5)
def C_NPB():  return curses.color_pair(6) | curses.A_BOLD
def C_FTR():  return curses.color_pair(7)
def C_MNU():  return curses.color_pair(8) | curses.A_BOLD
def C_BDR():  return curses.color_pair(9)


def fmt_time(v) -> str:
    if v is None:
        return "--:--"
    try:
        s = int(float(v))
        return f"{s // 60:02d}:{s % 60:02d}"
    except Exception:
        return "--:--"


def progress_bar(win, y: int, x: int, w: int, frac: float):
    inner  = max(0, w - 2)
    filled = int(inner * max(0.0, min(1.0, frac)))
    c_fill  = curses.color_pair(4) | curses.A_BOLD
    c_empty = curses.color_pair(3)
    try:
        win.addch(y, x, "▕", c_empty)
        for i in range(inner):
            win.addch(y, x + 1 + i,
                      "█" if i < filled else "░",
                      c_fill if i < filled else c_empty)
        win.addch(y, x + 1 + inner, "▏", c_empty)
    except curses.error:
        pass


def fill_row(win, y: int, w: int, attr: int, x: int = 0):
    try:
        win.attron(attr)
        win.addstr(y, x, " " * w)
        win.attroff(attr)
    except curses.error:
        pass


def safe_addstr(win, y: int, x: int, text: str, attr: int = 0):
    try:
        if attr:
            win.addstr(y, x, text, attr)
        else:
            win.addstr(y, x, text)
    except curses.error:
        pass


# ── Column helpers ────────────────────────────────────────────────────────────

def vline(win, x: int, y_start: int, y_end: int):
    for y in range(y_start, y_end + 1):
        safe_addstr(win, y, x, "│", C_BDR())


# ── Thumbnail panel ───────────────────────────────────────────────────────────

def draw_thumbnail_block(win, y0: int, x0: int, h: int, w: int, ascii_lines: list):
    inner_w = max(1, w - 1)
    for i, line in enumerate(ascii_lines[:h]):
        safe_addstr(win, y0 + i, x0, line[:inner_w].ljust(inner_w), C_NRM())


def draw_thumbnail_placeholder(win, y0: int, x0: int, h: int, w: int, label: str = ""):
    inner_w = max(4, w - 1)
    inner_h = max(3, h)
    mid     = inner_h // 2
    for row in range(inner_h):
        if row == 0:
            line = "┌" + "─" * (inner_w - 2) + "┐"
        elif row == inner_h - 1:
            line = "└" + "─" * (inner_w - 2) + "┘"
        elif row == mid - 1:
            line = "│" + "♫".center(inner_w - 2) + "│"
        elif row == mid:
            line = "│" + "NO ART".center(inner_w - 2) + "│"
        elif row == mid + 1:
            line = "│" + label[:inner_w - 2].center(inner_w - 2) + "│"
        else:
            line = "│" + " " * (inner_w - 2) + "│"
        safe_addstr(win, y0 + row, x0, line[:inner_w], C_ACC())


# ── ESC popup menu ────────────────────────────────────────────────────────────

MENU_RESUME  = 0
MENU_OPTIONS = 1
MENU_QUIT    = 2

_MENU_ITEMS = [
    (MENU_RESUME,  "▶  Reanudar"),
    (MENU_OPTIONS, "⚙  Opciones"),
    (MENU_QUIT,    "✕  Salir"),
]


def draw_esc_menu(win, selected: int):
    H, W = win.getmaxyx()
    box_h = len(_MENU_ITEMS) + 4
    box_w = 32
    y0    = max(0, (H - box_h) // 2)
    x0    = max(0, (W - box_w) // 2)

    for r in range(box_h):
        safe_addstr(win, y0 + r, x0, " " * box_w, C_NRM())

    safe_addstr(win, y0,           x0, "╔" + "═" * (box_w - 2) + "╗", C_BDR())
    safe_addstr(win, y0 + box_h-1, x0, "╚" + "═" * (box_w - 2) + "╝", C_BDR())
    for r in range(1, box_h - 1):
        safe_addstr(win, y0 + r, x0,             "║", C_BDR())
        safe_addstr(win, y0 + r, x0 + box_w - 1, "║", C_BDR())

    title = " MENÚ "
    safe_addstr(win, y0, x0 + (box_w - len(title)) // 2, title, C_HDR())

    for i, (_, label) in enumerate(_MENU_ITEMS):
        row  = y0 + 2 + i
        attr = C_MNU() if i == selected else C_NRM()
        fill_row(win, row, box_w - 2, attr, x0 + 1)
        safe_addstr(win, row, x0 + 3, label, attr)

    hint = "↑↓ mover · ENTER elegir · ESC cerrar"
    safe_addstr(win, y0 + box_h - 2, x0 + 1,
                hint[:box_w - 2].center(box_w - 2), C_YLW())
    win.refresh()
    return y0, x0, box_h, box_w