```
            ███████╗██████╗ ██████╗ ██╗  ██╗        ██████╗  ██████║   ████╗  ████████║
            ██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝        ██╔══██║ ██╔═══╝  ██╚ ██╗    ██╔══╝
            ███████╗██║  ██║██████╔╝ ╚███╔╝  █████  ██║ ██║  ██████║ ██╚   ██║   ██║
            ╚════██║██║  ██║██╔══██╗ ██╔██╗         ██║  ██║ ██╔═══╝ ████████║   ██║
            ███████║██████╔╝██║  ██║██╔╝ ██╗        ██████╔╝ ██████╗ ██║   ██║   ██║
            ╚══════╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝        ╚═════╝  ╚═════╝ ╚═╝   ╚═╝   ╚═╝
```

<div align="center">

# sadrach34 / SDRX-Beat

**Terminal music player** — local files + YouTube/radio stations, zero GUI.

![](https://img.shields.io/github/last-commit/Sadrach34/SDRX-Beat?style=for-the-badge&color=cba6f7&labelColor=1e1e2e&logo=git&logoColor=cdd6f4)
![](https://img.shields.io/github/stars/Sadrach34/SDRX-Beat?style=for-the-badge&color=f38ba8&labelColor=1e1e2e&logo=starship&logoColor=cdd6f4)
![](https://img.shields.io/github/repo-size/Sadrach34/SDRX-Beat?style=for-the-badge&color=a6e3a1&labelColor=1e1e2e&logo=files&logoColor=cdd6f4)

</div>

---

<div align="center">
  <h2>· what is it ·</h2>
</div>

SDRX-Beat is a **curses TUI music player** built on top of mpv. Browse and play your local music library or stream from YouTube playlists and internet radio stations — all from the terminal. Session state is preserved between launches so you resume exactly where you left off.

---

<div align="center">
  <h2>· features ·</h2>
</div>

<details open>
<summary><b>Core</b></summary>
<br>

| Feature | Description |
| --- | --- |
| **Local music** | Browse `~/Music/` recursively, supports mp3 · flac · wav · ogg · opus · m4a · aac |
| **Online stations** | Stream YouTube playlists and internet radio via yt-dlp + mpv |
| **Session restore** | Resumes last track/position on next launch |
| **Shuffle** | In-memory playlist shuffle with state saved to session |
| **Download** | `d` key downloads current track via yt-dlp to `~/Music/` |
| **Live search** | `Ctrl+T` filters the current list in real-time |
| **MPRIS** | Auto-detects mpris.so/lua → media key + desktop notification support |
| **Progress bar** | Live seek position + duration bar in the footer |

</details>

<details>
<summary><b>Supported formats</b></summary>
<br>

| Type | Formats |
| --- | --- |
| Local audio | `.mp3` `.flac` `.wav` `.ogg` `.opus` `.m4a` `.aac` `.mp4` |
| Online | YouTube playlists · YouTube streams · HTTP radio streams |

</details>

---

<div align="center">
  <h2>· keybindings ·</h2>
</div>

| Key | Action |
| --- | --- |
| `↑ ↓` | Navigate list |
| `PgUp PgDn` | Scroll 10 items |
| `Enter` | Play selected / open playlist |
| `Space` | Pause / Resume |
| `← →` | Seek ±5 seconds |
| `Ctrl+←` | Previous track |
| `Ctrl+→` | Next track |
| `Ctrl+T` | Search / filter current list |
| `Ctrl+S` | Stop playback |
| `s` | Shuffle local music |
| `d` | Download selected (yt-dlp) |
| `o` | Switch to Online Stations |
| `l` | Switch to Local Music |
| `r` | Refresh local file list |
| `Backspace / b` | Back to station list (from playlist view) |
| `q / ESC` | Quit |

---

<div align="center">
  <h2>· installation ·</h2>
</div>

### Quick install

```bash
git clone https://github.com/Sadrach34/SDRX-Beat.git
cd SDRX-Beat
bash install.sh
```

### What the installer does

- Copies project to `~/.config/sdrx-beat`
- Creates `~/.local/bin/beat` and `~/.local/bin/sdrx-beat` (system commands, no sudo needed)
- Adds optional shell integration for **update notifications** on `yay` / `sudo pacman -Syu`
- Detects common shell config files (zsh · bash · fish) and injects the integration only if an existing file is found
- If no shell config file is found, it prints the snippet so you can paste it manually into your shell init/shortcuts file

### After install

```bash
beat         # launch SDRX-Beat
sdrx-beat    # same
```

### Maintenance

```bash
beat --update
beat --repair
beat --uninstall
beat --help
```

Also supported:

```bash
beat -up
beat -R
beat -h
```

You will also see an update notification automatically next time you run `yay` or `sudo pacman -Syu`.

---

<div align="center">
  <h2>· dependencies ·</h2>
</div>

| Package | Required | Purpose |
| --- | --- | --- |
| `python3` | Yes | runtime |
| `mpv` | Yes | audio engine |
| `yt-dlp` | Yes | YouTube + playlist support |
| `mpv-mpris` | Optional | MPRIS / media keys |

Install on Arch:

```bash
sudo pacman -S python mpv yt-dlp
# optional MPRIS support:
yay -S mpv-mpris
```

---

<div align="center">
  <h2>· structure ·</h2>
</div>

```
SDRX-Beat/
├── main.py        # entry point
├── app.py         # TUI application class (input, draw loop)
├── draw.py        # curses rendering helpers
├── mpv.py         # mpv process + IPC management
├── session.py     # session persistence (~/.cache/rofibeats_session.json)
├── config.py      # static config (paths, keycodes, online stations)
├── assets/
│   └── SDRX.txt  # splash screen logo
└── install.sh     # installer
```

---

<div align="center">
  <h2>· credits ·</h2>
</div>

Repository maintained by [sadrach34](https://github.com/Sadrach34).

- **[mpv](https://mpv.io)** — media engine
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — YouTube extraction

---
## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Sadrach34/SDRX-Beat&type=Date)](https://star-history.com/#Sadrach34/SDRX-Beat&Date)

## 🤝 Contribution

<div align="center">
We welcome contributions of all kinds: bug fixes, new features, documentation improvements, and much more.
Please read the <a href=".github/CONTRIBUTING.md"><strong>Contribution Guide</strong></a> before submitting a pull request.
</div>

<br>

<div align="center">
  We thank all our contributors for their valuable contributions.
</div>

<div align="center">
  <a href="https://github.com/Sadrach34/SDRX-Beat/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=Sadrach34/SDRX-Beat" style="border-radius: 15px; box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);" />
  </a>
</div>

---

## License

Distributed under **GNU General Public License v3.0 (GPLv3)**. See `LICENSE`.
