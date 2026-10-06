#!/usr/bin/env bash
#
# Removes everything install.sh set up: the running dashboard, the login service, the
# app menu and autostart entries, the udev rules, the group and the Python environment.
# It asks before deleting your saved settings.
#
# System packages are left installed, because other programs may use them.
#
# Run it as your normal user:   ./uninstall.sh
# See what it would do first:   ./uninstall.sh --dry-run

set -euo pipefail

GROUP="asus-dashboard"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
RULES_TARGET="/etc/udev/rules.d/99-asus-dashboard.rules"
SERVICE_NAME="asus-dashboard.service"
SERVICE_TARGET="$HOME/.config/systemd/user/$SERVICE_NAME"
LAUNCHER="$HOME/.local/share/applications/asus-dashboard.desktop"
AUTOSTART="$HOME/.config/autostart/asus-dashboard.desktop"
SETTINGS_DIR="$HOME/.config/asus-dashboard"

DRY_RUN=0

step() {
    printf '\n==> %s\n' "$1"
}

note() {
    printf '    %s\n' "$1"
}

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would run: $*"
    else
        "$@"
    fi
}

confirm() {
    local answer
    read -r -p "    $1 [y/N] " answer
    [ "$answer" = "y" ] || [ "$answer" = "Y" ]
}

for argument in "$@"; do
    case "$argument" in
        --dry-run)
            DRY_RUN=1
            ;;
        -h | --help)
            sed -n '3,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $argument (try --help)" >&2
            exit 1
            ;;
    esac
done

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as your normal user, not with sudo. It asks for sudo itself when it needs it." >&2
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    step "Dry run: nothing will be changed"
fi

step "Stopping the dashboard"
if pgrep -u "$USER" -f "$VENV/bin/asus-dashboard" > /dev/null; then
    run pkill -u "$USER" -f "$VENV/bin/asus-dashboard"
else
    note "not running"
fi

step "Removing the login service"
if [ -f "$SERVICE_TARGET" ]; then
    run systemctl --user disable --now "$SERVICE_NAME"
    run rm -f "$SERVICE_TARGET"
    run systemctl --user daemon-reload
    [ "$DRY_RUN" -eq 1 ] || note "removed: $SERVICE_TARGET"
else
    note "not installed"
fi

step "Removing the app menu and autostart entries"
for entry in "$LAUNCHER" "$AUTOSTART"; do
    if [ -f "$entry" ]; then
        run rm -f "$entry"
        [ "$DRY_RUN" -eq 1 ] || note "removed: $entry"
    else
        note "not there: $entry"
    fi
done

step "Removing the udev rules"
if [ -f "$RULES_TARGET" ] || [ -f "$RULES_TARGET.bak" ]; then
    run sudo rm -f "$RULES_TARGET" "$RULES_TARGET.bak"
    run sudo udevadm control --reload-rules
    note "hardware files go back to root-only at the next reboot"
else
    note "not installed"
fi

step "Removing the $GROUP group"
if getent group "$GROUP" > /dev/null; then
    run sudo groupdel "$GROUP"
else
    note "does not exist"
fi

step "Removing the Python environment"
if [ -d "$VENV" ] && [ "$(basename "$VENV")" = ".venv" ]; then
    run rm -rf "$VENV"
    [ "$DRY_RUN" -eq 1 ] || note "removed: $VENV"
else
    note "not there: $VENV"
fi

step "Your saved settings"
if [ -d "$SETTINGS_DIR" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would ask whether to delete: $SETTINGS_DIR"
    elif confirm "Also delete your saved settings in $SETTINGS_DIR?"; then
        rm -rf "$SETTINGS_DIR"
        note "deleted"
    else
        note "kept"
    fi
else
    note "none saved"
fi

step "Finished"
if [ "$DRY_RUN" -eq 1 ]; then
    note "That was a dry run. Run ./uninstall.sh to do it for real."
else
    note "The dashboard is removed. This folder ($PROJECT_DIR) is left for you to delete."
fi
