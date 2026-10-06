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
    """Turn the warm screen tint on right now, or off.

    GNOME only tints the screen inside its schedule, which by default is sunset to sunrise, so
    switching night light on during the day shows nothing. Turning it on here therefore also
    sets an all-day schedule. Turning it off hands the schedule back to sunset-to-sunrise.
    """
    if enabled:
        commands = [
            ["gsettings", "set", SCHEMA, "night-light-schedule-automatic", "false"],
            ["gsettings", "set", SCHEMA, "night-light-schedule-from", "0.0"],
            ["gsettings", "set", SCHEMA, "night-light-schedule-to", "23.99"],
            ["gsettings", "set", SCHEMA, "night-light-enabled", "true"],
        ]
    else:
        commands = [
            ["gsettings", "set", SCHEMA, "night-light-enabled", "false"],
            ["gsettings", "set", SCHEMA, "night-light-schedule-automatic", "true"],
        ]

    ok = all(run_command(command) is not None for command in commands)
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