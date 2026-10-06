#!/usr/bin/env bash
#
# Sets up everything the ASUS Dashboard needs:
#   1. system packages        (sudo)
#   2. the asus-dashboard group, with you in it   (sudo)
#   3. udev rules that let that group change the hardware   (sudo)
#   4. a Python environment with the dashboard installed
#   5. a service that re-applies your settings at login
#   6. the app menu entry, and starting in the tray at login
#
# Run it as your normal user:   ./install.sh
# See what it would do first:   ./install.sh --dry-run
# It is safe to run again: steps that are already done are skipped.

set -euo pipefail

GROUP="asus-dashboard"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv"
RULES_SOURCE="$PROJECT_DIR/packaging/99-asus-dashboard.rules"
RULES_TARGET="/etc/udev/rules.d/99-asus-dashboard.rules"
SERVICE_NAME="asus-dashboard.service"
SERVICE_SOURCE="$PROJECT_DIR/packaging/$SERVICE_NAME"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_TARGET="$SERVICE_DIR/$SERVICE_NAME"
LAUNCHER="$HOME/.local/share/applications/asus-dashboard.desktop"
KEYBOARD_LED="/sys/class/leds/asus::kbd_backlight"

DRY_RUN=0
NEEDS_RELOGIN=0
PROBLEMS=0
MISSING_PACKAGES=()

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

require() {
    local package="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        note "found: $package"
    else
        note "missing: $package"
        MISSING_PACKAGES+=("$package")
    fi
}

check_access() {
    local file="$1"
    if [ ! -e "$file" ]; then
        note "not on this laptop: $file"
    elif [ "$(stat -c %G "$file")" = "$GROUP" ]; then
        note "ready: $file"
    else
        note "NOT ready: $file"
        PROBLEMS=1
    fi
}

for argument in "$@"; do
    case "$argument" in
        --dry-run)
            DRY_RUN=1
            ;;
        -h | --help)
            sed -n '3,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

if ! command -v python3 > /dev/null; then
    echo "python3 is missing. Install it with: sudo apt install python3" >&2
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    step "Dry run: nothing will be changed"
fi

step "Checking system packages"
require python3-venv python3 -c "import ensurepip, venv"
require python3-dbus python3 -c "import dbus"
require python3-gi python3 -c "import gi"
require libxcb-cursor0 sh -c "ldconfig -p | grep -q 'libxcb-cursor.so.0'"
if [ "${#MISSING_PACKAGES[@]}" -gt 0 ]; then
    if ! command -v apt-get > /dev/null; then
        echo "These packages are missing and this system has no apt-get: ${MISSING_PACKAGES[*]}" >&2
        exit 1
    fi
    run sudo apt-get install -y "${MISSING_PACKAGES[@]}"
fi

step "Setting up the $GROUP group"
if getent group "$GROUP" > /dev/null; then
    note "group exists"
else
    run sudo groupadd "$GROUP"
fi
if id -nG "$USER" | tr ' ' '\n' | grep -qx "$GROUP"; then
    note "$USER is a member"
else
    run sudo usermod -aG "$GROUP" "$USER"
fi
if ! id -nG | tr ' ' '\n' | grep -qx "$GROUP"; then
    NEEDS_RELOGIN=1
fi

step "Installing the udev rules"
if [ -f "$RULES_TARGET" ] && cmp -s "$RULES_SOURCE" "$RULES_TARGET"; then
    note "up to date: $RULES_TARGET"
else
    if [ -f "$RULES_TARGET" ]; then
        run sudo cp "$RULES_TARGET" "$RULES_TARGET.bak"
        note "the previous rules are kept as $RULES_TARGET.bak"
    fi
    run sudo install -m 644 "$RULES_SOURCE" "$RULES_TARGET"
    run sudo udevadm control --reload-rules
    run sudo udevadm trigger --action=add --subsystem-match=leds
    run sudo udevadm trigger --action=bind --subsystem-match=platform --sysname-match=asus-nb-wmi
    run sudo udevadm settle
fi

step "Checking hardware access"
check_access "$KEYBOARD_LED/brightness"
check_access "$KEYBOARD_LED/kbd_rgb_mode"
for battery in /sys/class/power_supply/BAT*; do
    check_access "$battery/charge_control_end_threshold"
done

step "Installing the dashboard into its own Python environment"
if [ -x "$VENV/bin/python" ]; then
    note "using the existing environment: $VENV"
else
    run python3 -m venv --system-site-packages "$VENV"
    note "created: $VENV"
fi
note "installing the package and anything it needs (this can take a minute the first time)"
run "$VENV/bin/pip" install --quiet --editable "$PROJECT_DIR"

step "Installing the login service"
generated_service="$(sed "s|@VENV@|$VENV|" "$SERVICE_SOURCE")"
if [ -f "$SERVICE_TARGET" ] && [ "$(cat "$SERVICE_TARGET")" = "$generated_service" ]; then
    note "up to date: $SERVICE_TARGET"
else
    run mkdir -p "$SERVICE_DIR"
    if [ "$DRY_RUN" -eq 1 ]; then
        note "would write: $SERVICE_TARGET"
    else
        printf '%s\n' "$generated_service" > "$SERVICE_TARGET"
        note "wrote: $SERVICE_TARGET"
    fi
    run systemctl --user daemon-reload
fi
if systemctl --user is-enabled --quiet "$SERVICE_NAME" 2> /dev/null; then
    note "already enabled"
else
    run systemctl --user enable "$SERVICE_NAME"
fi

step "Adding the dashboard to the app menu"
if [ -f "$LAUNCHER" ]; then
    run "$VENV/bin/asus-dashboard-install" --refresh
else
    run "$VENV/bin/asus-dashboard-install"
fi

step "Finished"
if [ "$DRY_RUN" -eq 1 ]; then
    note "That was a dry run. Run ./install.sh to do it for real."
    exit 0
fi
if [ "$NEEDS_RELOGIN" -eq 1 ]; then
    note "Reboot (or log out and back in) so your new group membership takes effect."
    note "Until then, changing the keyboard light or charge limit will be refused."
elif [ "$PROBLEMS" -eq 1 ]; then
    note "Some hardware files are not ready yet (see above). A reboot usually fixes that."
fi
note "Start it from the app menu (search for ASUS), or run: $VENV/bin/asus-dashboard"
