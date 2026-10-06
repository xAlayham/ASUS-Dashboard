"""Add the dashboard to the app menu and make it start, hidden in the tray, at every login.

Run:  python3 install_desktop.py            to install both entries
      python3 install_desktop.py --remove   to remove them again
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
ENTRY_NAME = "asus-dashboard.desktop"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"


def find_python() -> Path:
    """Return the Python that has PySide6: the project's .venv if it exists, otherwise the one running this script"""
    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def build_entry(hidden: bool) -> str:
    """Return the text of a .desktop file that starts the dashboard, optionally hidden in the tray"""
    command = f'"{find_python()}" "{PROJECT_DIR / "dashboard.py"}"'
    if hidden:
        command += " --hidden"
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=ASUS Dashboard",
        "Comment=Control panel for ASUS laptops",
        f"Exec={command}",
        f"Icon={PROJECT_DIR / 'assets' / 'icon.svg'}",
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


def install(applications_dir: Path = APPLICATIONS_DIR, autostart_dir: Path = AUTOSTART_DIR) -> list[Path]:
    """Write the launcher and the autostart entry. Return the paths of the files written"""
    written = []
    for folder, hidden in ((applications_dir, False), (autostart_dir, True)):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / ENTRY_NAME
        path.write_text(build_entry(hidden))
        written.append(path)
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


if __name__ == "__main__":
    if "--remove" in sys.argv:
        for removed_path in remove():
            print(f"Removed {removed_path}")
        print("The dashboard is no longer in the app menu and will not start at login.")
    else:
        for written_path in install():
            print(f"Wrote {written_path}")
        print("The dashboard is now in the app menu and will start in the tray at login.")
