#!/usr/bin/env python3
"""
RofiBeats TUI — entry point
Run: python3 main.py
Created by Sadrach Garcia (SDRX) on 2026-05-09

Keybindings:
  ENTER          Play selected / open playlist
  SPACE          Pause / Play
  ← →            Seek ±5 seconds
  Ctrl+←         Previous track
  Ctrl+→         Next track
  Ctrl+T         Search / filter current list
  Ctrl+S         Stop
  Backspace / b  Back to station list (from playlist view)
  s              Shuffle local music
  d              Download selected (yt-dlp)
  o              Switch to Online Stations
  l              Switch to Local Music
  r              Refresh local file list
  q / ESC        Quit
"""
import curses
import sys
import os

# Make sure imports resolve from this directory
sys.path.insert(0, os.path.dirname(__file__))

from app import App
import draw

_LOGO = os.path.join(os.path.dirname(__file__), "assets", "SDRX.txt")


def main():
    def _run(stdscr):
        draw.splash_screen(stdscr, _LOGO)
        App(stdscr).run()
    curses.wrapper(_run)


if __name__ == "__main__":
    main()
