# Contributing to SDRX-Beat 🎵

Thank you for considering contributing to SDRX-Beat! Bug fixes, features, and docs are all welcome.

---

### 🛠️ How Can You Contribute?

1. **Bug Reports:** Playback issues, crashes, IPC errors, session restore failures? Open an issue.
2. **Feature Requests:** New keybinds, online source support, UI improvements.
3. **Code Contributions:** Submit a Pull Request for fixes or features.
4. **Documentation:** Improve the README or clarify keybindings/dependencies.

---

### 🚀 Pull Request Process

1. **Fork the repo** and create your branch from `main`.
2. **Test your changes.** Run `beat` and verify local playback, online stations, shuffle, and session restore still work.
3. **Follow the Style Guide:**
   - Use **Conventional Commits** (e.g., `feat: add seek bar`, `fix: mpv ipc timeout`).
   - Keep modules focused: `mpv.py` for IPC, `app.py` for input/state, `draw.py` for rendering, `session.py` for persistence.
4. **Update Documentation:** New keybind or dependency? Update the README table.
5. **Open the PR:** Clear description of what changed and why.

---

### 🎨 Design Philosophy

- **Terminal-first:** No GUI dependencies. Everything lives in the curses TUI.
- **Minimal deps:** Core stack is `python3 + mpv + yt-dlp`. Don't add packages without good reason.
- **Session integrity:** Changes to playback state must be reflected in `session.py` so state survives restarts.
- **Non-blocking:** Heavy operations (yt-dlp fetch, IPC calls) must not freeze the draw loop. Use threads.

---

### 📁 Project Structure

```
SDRX-Beat/
├── main.py        # entry point
├── app.py         # TUI app class (input loop, state machine)
├── draw.py        # curses rendering
├── mpv.py         # mpv process + IPC management
├── session.py     # session persistence
├── config.py      # static config (paths, keycodes, stations)
└── install.sh     # installer
```

---

### ⚖️ Code of Conduct

Be respectful. We're all here to build better tools.
