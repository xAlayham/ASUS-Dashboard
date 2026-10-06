import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "asus-dashboard"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

def load_settings() -> dict:
    """Return all saved settings as a dictionary, or an empty dictionary if there are none yet."""
    try:
        return json.loads(SETTINGS_FILE.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Warning: {SETTINGS_FILE} is damaged, ignoring it")
        return {}

def save_setting(key: str, value: int | str | bool | dict) -> None:
    """Save one setting to disk without changing all the other settings"""
    settings = load_settings()
    settings[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=4))

def get_setting(key: str, default: int | str | bool | dict | None = None) -> int | str | bool | dict | None:
    """Returns one saved setting or 'default' if it has never been saved"""
    return load_settings().get(key, default)

if __name__ == "__main__":
    print("Before:", load_settings())
    save_setting("test_number", 42)
    save_setting("test_word", "hello")
    print("After:", load_settings())
    print("test_number =", get_setting("test_number"))
    print("missing    =", get_setting("does_not_exist", "fallback"))