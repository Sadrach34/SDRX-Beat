#!/usr/bin/env bash
# SDRX-Beat installer
# Created by Sadrach Garcia (SDRX) on 2026-05-09
# Usage: bash install.sh [--update] [--uninstall]

set -euo pipefail

# ── constants ──────────────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.config/sdrx-beat"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/Sadrach34/SDRX-Beat.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKER="$INSTALL_DIR/.sdrx-beat-installed"

# ── colors ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'
BLU='\033[0;34m'; MAG='\033[0;35m'; CYN='\033[0;36m'
BLD='\033[1m'; RST='\033[0m'

ok()   { echo -e "${GRN}${BLD}[✓]${RST} $*"; }
info() { echo -e "${BLU}${BLD}[·]${RST} $*"; }
warn() { echo -e "${YLW}${BLD}[!]${RST} $*"; }
err()  { echo -e "${RED}${BLD}[✗]${RST} $*" >&2; }
hdr()  { echo -e "\n${MAG}${BLD}── $* ──${RST}"; }

# ── logo ───────────────────────────────────────────────────────────────────────
print_logo() {
    echo -e "${CYN}${BLD}"
    cat << 'EOF'
      ███████╗██████╗ ██████╗ ██╗  ██╗        ██████╗  ██████║   ████╗  ████████║
      ██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝        ██╔══██║ ██╔═══╝  ██╚ ██╗    ██╔══╝
    ███████╗██║  ██║██████╔╝ ╚███╔╝  █████  ██║ ██║  ██████║ ██╚   ██║   ██║
    ╚════██║██║  ██║██╔══██╗ ██╔██╗         ██║  ██║ ██╔═══╝ ████████║   ██║
    ███████║██████╔╝██║  ██║██╔╝ ██╗        ██████╔╝ ██████╗ ██║   ██║   ██║
    ╚══════╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝        ╚═════╝  ╚═════╝ ╚═╝   ╚═╝   ╚═╝
EOF
    echo -e "${RST}"
}

# ── dependency check ───────────────────────────────────────────────────────────
check_deps() {
    hdr "Checking dependencies"
    local missing=()

    for dep in python3 mpv yt-dlp; do
        if command -v "$dep" &>/dev/null; then
            ok "$dep found"
        else
            warn "$dep not found"
            missing+=("$dep")
        fi
    done

    if ! command -v mpv-mpris &>/dev/null 2>&1 && \
       ! ls /etc/mpv/scripts/mpris.* /usr/lib/mpv/scripts/mpris.* \
             "$HOME/.config/mpv/scripts/mpris."* 2>/dev/null | grep -q .; then
        info "mpv-mpris not found (optional — needed for MPRIS / media keys)"
        info "  Install with: yay -S mpv-mpris"
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo ""
        err "Missing required packages: ${missing[*]}"
        echo -e "  Install with: ${CYN}sudo pacman -S ${missing[*]}${RST}"
        echo ""
        read -rp "Continue anyway? [y/N] " ans
        [[ "${ans,,}" == "y" ]] || exit 1
    fi
}

# ── copy files ─────────────────────────────────────────────────────────────────
install_files() {
    hdr "Installing files"

    mkdir -p "$INSTALL_DIR"

    local files=(main.py app.py draw.py mpv.py session.py config.py)
    for f in "${files[@]}"; do
        if [[ -f "$SCRIPT_DIR/$f" ]]; then
            cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
            ok "Copied $f"
        fi
    done

    if [[ -d "$SCRIPT_DIR/assets" ]]; then
        cp -r "$SCRIPT_DIR/assets" "$INSTALL_DIR/"
        ok "Copied assets/"
    fi

    # Mark as git-tracked install if we're inside the repo
    if [[ -d "$SCRIPT_DIR/.git" ]]; then
        cp -r "$SCRIPT_DIR/.git" "$INSTALL_DIR/.git"
        ok "Copied .git (enables update tracking)"
    fi

    touch "$MARKER"
    ok "Installation marker created"
}

# ── git-based update ───────────────────────────────────────────────────────────
update_files() {
    hdr "Updating SDRX-Beat"

    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        warn "No .git found in $INSTALL_DIR — cloning fresh from GitHub"
        rm -rf "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
        ok "Cloned $REPO_URL"
        return
    fi

    info "Pulling latest changes…"
    git -C "$INSTALL_DIR" pull --ff-only origin main 2>&1 | while IFS= read -r line; do
        info "$line"
    done
    ok "Update complete"
}

# ── launcher wrappers ──────────────────────────────────────────────────────────
install_commands() {
    hdr "Installing commands"
    mkdir -p "$BIN_DIR"

    for cmd in beat sdrx-beat; do
        cat > "$BIN_DIR/$cmd" << EOF
#!/usr/bin/env bash
# SDRX-Beat launcher
INSTALL_DIR="\$HOME/.config/sdrx-beat"
case "\${1:-}" in
    --update|-u) exec bash "\$INSTALL_DIR/install.sh" --update ;;
    --uninstall) exec bash "\$INSTALL_DIR/install.sh" --uninstall ;;
esac
exec python3 "\$INSTALL_DIR/main.py" "\$@"
EOF
        chmod +x "$BIN_DIR/$cmd"
        ok "Created $BIN_DIR/$cmd"
    done

    # Warn if ~/.local/bin is not in PATH
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        warn "$BIN_DIR is not in your PATH"
        info "  Add to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# ── check-update helper ────────────────────────────────────────────────────────
install_check_update_script() {
    cat > "$INSTALL_DIR/check-update.sh" << 'SCRIPT'
#!/usr/bin/env bash
# SDRX-Beat update checker — sourced by shell integration
_sdrx_beat_check_update() {
    local dir="$HOME/.config/sdrx-beat"
    [[ -d "$dir/.git" ]] || return 0
    # Fetch quietly; skip if offline
    git -C "$dir" fetch origin --quiet 2>/dev/null || return 0
    local behind
    behind=$(git -C "$dir" rev-list HEAD..origin/main --count 2>/dev/null) || return 0
    [[ "$behind" -gt 0 ]] || return 0
    echo -e "\033[1;35m[SDRX-Beat]\033[0m \033[1;33mUpdate available\033[0m ($behind commit(s) behind). Run: \033[1;36msdrx-beat --update\033[0m"
}
SCRIPT
    chmod +x "$INSTALL_DIR/check-update.sh"
    ok "Created check-update.sh"
}

# ── shell integration snippet ──────────────────────────────────────────────────
_posix_snippet() {
    cat << 'SNIPPET'

# ── SDRX-Beat shell integration ───────────────────────────────────────────────
if [[ -f "$HOME/.config/sdrx-beat/check-update.sh" ]]; then
    source "$HOME/.config/sdrx-beat/check-update.sh"
fi

# Wrap yay to show SDRX-Beat update notice
if command -v yay &>/dev/null; then
    function yay() {
        _sdrx_beat_check_update
        command yay "$@"
    }
fi
# ── end SDRX-Beat ─────────────────────────────────────────────────────────────
SNIPPET
}

_zsh_snippet() {
    cat << 'SNIPPET'

# ── SDRX-Beat shell integration ───────────────────────────────────────────────
if [[ -f "$HOME/.config/sdrx-beat/check-update.sh" ]]; then
    source "$HOME/.config/sdrx-beat/check-update.sh"
fi

# preexec: show SDRX-Beat update notice before yay or sudo pacman -Syu
_sdrx_beat_preexec() {
    case "$1" in
        yay\ *|yay|sudo\ pacman\ *-Syu*|sudo\ pacman\ *-Syuu*)
            _sdrx_beat_check_update ;;
    esac
}
autoload -Uz add-zsh-hook 2>/dev/null
add-zsh-hook preexec _sdrx_beat_preexec 2>/dev/null

# Ensure ~/.local/bin is in PATH
[[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && export PATH="$HOME/.local/bin:$PATH"
# ── end SDRX-Beat ─────────────────────────────────────────────────────────────
SNIPPET
}

_bash_snippet() {
    cat << 'SNIPPET'

# ── SDRX-Beat shell integration ───────────────────────────────────────────────
if [[ -f "$HOME/.config/sdrx-beat/check-update.sh" ]]; then
    source "$HOME/.config/sdrx-beat/check-update.sh"
fi

# Wrap yay to show SDRX-Beat update notice
if command -v yay &>/dev/null; then
    function yay() {
        _sdrx_beat_check_update
        command yay "$@"
    }
fi

# Ensure ~/.local/bin is in PATH
[[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && export PATH="$HOME/.local/bin:$PATH"
# ── end SDRX-Beat ─────────────────────────────────────────────────────────────
SNIPPET
}

_fish_snippet() {
    cat << 'SNIPPET'

# ── SDRX-Beat shell integration ───────────────────────────────────────────────
function _sdrx_beat_check_update
    set dir "$HOME/.config/sdrx-beat"
    test -d "$dir/.git" || return
    git -C $dir fetch origin --quiet 2>/dev/null
    set behind (git -C $dir rev-list HEAD..origin/main --count 2>/dev/null)
    if test -n "$behind" -a "$behind" -gt 0
        echo -e "\033[1;35m[SDRX-Beat]\033[0m \033[1;33mUpdate available\033[0m ($behind commits). Run: \033[1;36msdrx-beat --update\033[0m"
    end
end

function fish_preexec --on-event fish_preexec
    switch $argv[1]
        case 'yay*' 'sudo pacman*-Syu*'
            _sdrx_beat_check_update
    end
end

fish_add_path "$HOME/.local/bin"
# ── end SDRX-Beat ─────────────────────────────────────────────────────────────
SNIPPET
}

# ── inject into shell config ───────────────────────────────────────────────────
_inject_if_missing() {
    local config_file="$1"
    local snippet="$2"
    local marker="SDRX-Beat shell integration"

    if grep -q "$marker" "$config_file" 2>/dev/null; then
        info "Shell integration already present in $config_file"
        return
    fi

    printf '%s' "$snippet" >> "$config_file"
    ok "Added shell integration to $config_file"
}

install_shell_integration() {
    hdr "Shell integration"

    install_check_update_script

    local configured=0

    # zsh
    if [[ -f "$HOME/.zshrc" ]] || [[ "$SHELL" == *zsh* ]]; then
        local zshrc="${ZDOTDIR:-$HOME}/.zshrc"
        touch "$zshrc"
        _inject_if_missing "$zshrc" "$(_zsh_snippet)"
        configured=1
    fi

    # bash
    if [[ -f "$HOME/.bashrc" ]]; then
        _inject_if_missing "$HOME/.bashrc" "$(_bash_snippet)"
        configured=1
    fi

    # fish
    if command -v fish &>/dev/null && [[ -d "$HOME/.config/fish" ]]; then
        local fish_cfg="$HOME/.config/fish/config.fish"
        touch "$fish_cfg"
        _inject_if_missing "$fish_cfg" "$(_fish_snippet)"
        configured=1
    fi

    if [[ "$configured" -eq 0 ]]; then
        warn "Could not detect shell config. Add this to your shell init file:"
        echo ""
        _posix_snippet
    fi
}

# ── uninstall ──────────────────────────────────────────────────────────────────
do_uninstall() {
    hdr "Uninstalling SDRX-Beat"

    rm -f "$BIN_DIR/beat" "$BIN_DIR/sdrx-beat"
    ok "Removed launcher commands"

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        ok "Removed $INSTALL_DIR"
    fi

    local marker="SDRX-Beat shell integration"
    local end_marker="end SDRX-Beat"

    for cfg in "${ZDOTDIR:-$HOME}/.zshrc" "$HOME/.bashrc" "$HOME/.config/fish/config.fish"; do
        if [[ -f "$cfg" ]] && grep -q "$marker" "$cfg"; then
            # Remove block between the two markers
            sed -i "/# ── $marker/,/# ── $end_marker/d" "$cfg"
            ok "Cleaned shell integration from $cfg"
        fi
    done

    ok "Uninstall complete"
}

# ── --update shortcut (called via sdrx-beat --update) ─────────────────────────
do_update() {
    print_logo
    update_files
    install_commands
    install_check_update_script
    echo ""
    ok "SDRX-Beat updated."
}

# ── main ───────────────────────────────────────────────────────────────────────
main() {
    print_logo

    case "${1:-}" in
        --update|-u)
            do_update
            exit 0
            ;;
        --uninstall|--remove)
            do_uninstall
            exit 0
            ;;
        ""|--install|-i)
            : # fall through to full install
            ;;
        *)
            echo "Usage: bash install.sh [--install | --update | --uninstall]"
            exit 1
            ;;
    esac

    # Full install
    if [[ -f "$MARKER" ]]; then
        warn "SDRX-Beat already installed at $INSTALL_DIR"
        read -rp "Re-install / update? [y/N] " ans
        if [[ "${ans,,}" == "y" ]]; then
            if [[ -d "$INSTALL_DIR/.git" ]]; then
                do_update
                exit 0
            fi
        else
            exit 0
        fi
    fi

    check_deps
    install_files
    install_commands
    install_shell_integration

    echo ""
    echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
    echo -e "${GRN}${BLD}  SDRX-Beat installed successfully!${RST}"
    echo -e "${GRN}${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
    echo ""
    echo -e "  Launch with: ${CYN}${BLD}beat${RST}  or  ${CYN}${BLD}sdrx-beat${RST}"
    echo -e "  Update with: ${CYN}${BLD}sdrx-beat --update${RST}"
    echo ""
    echo -e "  ${YLW}Reload your shell or run:${RST} ${CYN}source ~/.zshrc${RST}"
    echo ""
}

main "$@"
