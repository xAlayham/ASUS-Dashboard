from status import run_command
from settings import save_setting

SCHEMA = "org.gnome.settings-daemon.plugins.color"

def get_night_light() -> bool | None:
    """Return True if night light is on, Flase if off, returns None if unkown"""
    output = run_command(["gsettings", "get", SCHEMA, "night-light-enabled"])
    if output is None:
        return None
    return output == "true"

def get_night_light_temperature() -> int | None:
    """Return the night light warmth in Kelvin (lower = more orange), or None"""
    output = run_command(["gsettings", "get", SCHEMA, "night-light-temperature"])
    if output is None:
        return None
    return int(output.split()[-1])

def set_night_light(enabled: bool) -> bool:
    """Turn night light on or off"""
    value = "true" if enabled else "false"
    ok = run_command(["gsettings", "set", SCHEMA, "night-light-enabled", value]) is not None
    if ok:
        save_setting("night_light", enabled)
    return ok

def set_night_light_temperature(kelvin: int) -> bool:
    """Set how warm night light looks, between 1700 K (very orange) and  4700 K (mildly orange)"""
    if not 1700 <= kelvin <= 4700:
        print("Temperature must be between 1700 and 4700 K")
        return False
    ok = run_command(["gsettings", "set", SCHEMA, "night-light-temperature", str(kelvin)]) is not None
    if ok:
        save_setting("night_light_temperature", kelvin)
    return ok

if __name__ == "__main__":
    print("Night light on?", get_night_light())
    print("Temperature:", get_night_light_temperature())
    print("Set 3000 K:", set_night_light_temperature(3000))
    print("Set 9000 K:", set_night_light_temperature(9000))
    print("Temperature now:", get_night_light_temperature())
    print("Set back to 2700 K:", set_night_light_temperature(2700))