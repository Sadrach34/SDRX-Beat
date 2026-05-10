"""
draw.py – curses drawing helpers for RofiBeats TUI
Created by Sadrach Garcia (SDRX) on 2026-05-09
"""
import curses
import time


def splash_screen(stdscr, logo_path: str):
    """Show SDRX logo centered for 2 seconds before main UI starts."""
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
    curses.init_pair(1, curses.COLOR_BLACK,  curses.COLOR_CYAN)   # header / selected
    curses.init_pair(2, curses.COLOR_CYAN,   -1)                  # accent
    curses.init_pair(3, curses.COLOR_WHITE,  -1)                  # normal text
    curses.init_pair(4, curses.COLOR_GREEN,  -1)                  # playing / green
    curses.init_pair(5, curses.COLOR_YELLOW, -1)                  # yellow / status
    curses.init_pair(6, curses.COLOR_BLACK,  curses.COLOR_GREEN)  # now-playing bar
    curses.init_pair(7, curses.COLOR_WHITE,  curses.COLOR_BLACK)  # footer hints


# Colour shortcuts (call after init_colors)
def C_HDR():  return curses.color_pair(1) | curses.A_BOLD
def C_ACC():  return curses.color_pair(2) | curses.A_BOLD
def C_NRM():  return curses.color_pair(3)
def C_SEL():  return curses.color_pair(1) | curses.A_BOLD
def C_GRN():  return curses.color_pair(4) | curses.A_BOLD
def C_YLW():  return curses.color_pair(5)
def C_NPB():  return curses.color_pair(6) | curses.A_BOLD
def C_FTR():  return curses.color_pair(7)


def fmt_time(v) -> str:
    if v is None:
        return "--:--"
    try:
        s = int(float(v))
        return f"{s // 60:02d}:{s % 60:02d}"
    except Exception:
        return "--:--"


def progress_bar(win, y: int, x: int, w: int, frac: float):
    """Draw a ▕░░█████░░▏ progress bar."""
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


def fill_row(win, y: int, w: int, attr: int):
    """Paint a full-width row with attr."""
    try:
        win.attron(attr)
        win.addstr(y, 0, " " * w)
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
