"""Add the dashboard to the app menu and make it start, hidden in the tray, at every login.

Run:  asus-dashboard-install             to install both entries
      asus-dashboard-install --refresh   to rewrite the launcher, and the autostart entry only if it is on
      asus-dashboard-install --remove    to remove them again
"""
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent.resolve()
COMMAND_NAME = "asus-dashboard"
ENTRY_NAME = "asus-dashboard.desktop"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"


def find_command() -> str:
    """Return the command that starts the dashboard, with full paths.

    The asus-dashboard command is installed next to the Python that is running this code, so it
    is looked for there. If it is missing, the package is started through that Python instead.
    """
    command = Path(sys.executable).parent / COMMAND_NAME
    if command.exists():
        return f'"{command}"'
    return f'"{sys.executable}" -m asus_dashboard'


def build_entry(hidden: bool) -> str:
    """Return the text of a .desktop file that starts the dashboard, optionally hidden in the tray"""
    command = find_command()
    if hidden:
        command += " --hidden"
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=ASUS Dashboard",
        "Comment=Control panel for ASUS laptops",
        f"Exec={command}",
        f"Icon={PACKAGE_DIR / 'assets' / 'icon.svg'}",
        "Terminal=false",
        "Categories=Settings;HardwareSettings;",
        "StartupWMClass=asus-dashboard",
    ]
    if hidden:
        lines.append("X-GNOME-Autostart-enabled=true")
    return "\n".join(lines) + "\n"


def is_autostart_enabled(autostart_dir: Path = AUTOSTART_DIR) -> bool:
    """Return True if the dashboard is set to start at login"""
    return (autostart_dir / ENTRY_NAME).exists()


def set_autostart(enabled: bool, autostart_dir: Path = AUTOSTART_DIR) -> bool:
    """Turn starting at login on or off by writing or deleting the autostart entry. Return True if it worked"""
    path = autostart_dir / ENTRY_NAME
    try:
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(build_entry(hidden=True))
        elif path.exists():
            path.unlink()
        return True
    except OSError as e:
        print(f"Could not change the autostart entry {path}: {e}")
        return False


def write_launcher(applications_dir: Path = APPLICATIONS_DIR) -> Path:
    """Write the app menu entry and return its path"""
    applications_dir.mkdir(parents=True, exist_ok=True)
    path = applications_dir / ENTRY_NAME
    path.write_text(build_entry(hidden=False))
    return path


def install(applications_dir: Path = APPLICATIONS_DIR, autostart_dir: Path = AUTOSTART_DIR) -> list[Path]:
    """Write the launcher and the autostart entry. Return the paths of the files written"""
    written = [write_launcher(applications_dir)]
    if set_autostart(True, autostart_dir):
        written.append(autostart_dir / ENTRY_NAME)
    return written


def refresh(applications_dir: Path = APPLICATIONS_DIR, autostart_dir: Path = AUTOSTART_DIR) -> list[Path]:
    """Rewrite the launcher, and the autostart entry only if it is already on.

    Used when updating: paths may have changed, but whether to start at login is the user's
    choice and must not be switched back on behind their back.
    """
    written = [write_launcher(applications_dir)]
    if is_autostart_enabled(autostart_dir) and set_autostart(True, autostart_dir):
        written.append(autostart_dir / ENTRY_NAME)
    return written


def remove(applications_dir: Path = APPLICATIONS_DIR, autostart_dir: Path = AUTOSTART_DIR) -> list[Path]:
    """Delete the launcher and the autostart entry if they exist. Return the paths of the files removed"""
    removed = []
    for folder in (applications_dir, autostart_dir):
        path = folder / ENTRY_NAME
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def main() -> None:
    """Install or remove the entries. This is what the asus-dashboard-install command runs"""
    if "--remove" in sys.argv:
        for removed_path in remove():
            print(f"Removed {removed_path}")
        print("The dashboard is no longer in the app menu and will not start at login.")
    elif "--refresh" in sys.argv:
        for written_path in refresh():
            print(f"Wrote {written_path}")
    else:
        for written_path in install():
            print(f"Wrote {written_path}")
        print("The dashboard is now in the app menu and will start in the tray at login.")


if __name__ == "__main__":
    main()
