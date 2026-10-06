from asus_dashboard.settings import save_setting
from asus_dashboard.dbus_helpers import get_property, set_property
import dbus

MUTTER = "org.gnome.Mutter.DisplayConfig"
MUTTER_PATH = "/org/gnome/Mutter/DisplayConfig"
CONNECTOR = "eDP-1"
TEMPORARY = 1

POWER = "org.gnome.SettingsDaemon.Power"
POWER_PATH = "/org/gnome/SettingsDaemon/Power"
SCREEN = "org.gnome.SettingsDaemon.Power.Screen"
MIN_SCREEN_BRIGHTNESS = 5

def get_display_config():
    """Return a proxy for GNOME`s display service, or None if it isn't running"""
    try:
        bus = dbus.SessionBus()
        obj = bus.get_object(MUTTER, MUTTER_PATH)
        return dbus.Interface(obj, MUTTER)
    except dbus.exceptions.DBusException as e:
        print(f"Display service not available: {e.get_dbus_message()}")
        return None

def get_display_state() -> tuple[int, list, list] | None:
    """Ask GNOME for the current screen setup. Return (serial, monitors) or None"""
    config = get_display_config()
    if config is None:
        return None
    try:
        serial, monitors, logical_monitors, properties = config.GetCurrentState()
    except dbus.exceptions.DBusException as e:
        print(f"Could not read display state: {e.get_dbus_message()}")
        return None
    return int(serial), monitors, logical_monitors

def get_modes() -> list[dict]:
    """Return every mode the built-in screen supports, as simple dicts"""
    state = get_display_state()
    if state is None:
        return []
    serial, monitors, _ = state

    for monitor in monitors:
        info, modes, monitor_properties = monitor
        if str(info[0]) != CONNECTOR:
            continue

        result = []
        for mode in modes:
            mode_id, width, height, rate, preferred_scale, scales, flags = mode
            result.append({
                "id": str(mode_id),
                "width": int(width),
                "height": int(height),
                "rate": round(float(rate)),
                "current": bool(flags.get("is-current", False)),
            })
        return result
    return []

def get_current_mode() -> dict | None:
    """Finds the mode with "current": True and returns it, or returns None"""
    for mode in get_modes():
        if mode["current"]:
            return mode
    return None

def get_refresh_rates() -> list[int]:
    """Returns the refresh rates available at the current resolution, without duplication"""
    current = get_current_mode()
    if current is None:
        return []
    result =[]
    for mode in get_modes():
        if mode["width"] == current["width"] and mode["height"] == current["height"] and mode["rate"] not in result:
            result.append(mode["rate"])
    return result

def get_current_refresh_rate() -> int | None:
    """Returns current active refresh rate, or None"""
    current = get_current_mode()
    if current is None:
        return None
    return current["rate"]

def set_refresh_rate(rate: int) -> bool:
    """Changes refresh rate and returns True if refresh rate was changed sucessfully, else returns False"""
    valid_rates = get_refresh_rates()
    if rate not in valid_rates:
        print(f"Valid refresh rates: {get_refresh_rates()}")
        return False

    current = get_current_mode()
    if current is None:
        return False
    mode_id = None
    for mode in get_modes():
        if (mode["width"] == current["width"] and mode["height"] == current["height"] and mode["rate"] == rate):
            mode_id = mode["id"]
            break
    if mode_id is None:
        return False

    state = get_display_state()
    if state is None:
        return False
    serial, monitors, logical_monitors = state

    if len(monitors) > 1:
        print("External monitor connected, not supported yet")
        return False

    proxy = get_display_config()
    if proxy is None:
        return False

    connector = monitors[0][0][0]
    x, y, scale, transform, primary = logical_monitors[0][:5]
    layout = (x, y, scale, transform, primary, [(connector, mode_id, {})])
    try:
        proxy.ApplyMonitorsConfig(serial, TEMPORARY, [layout], {})
    except dbus.exceptions.DBusException as e:
        print(f"Failed to set refresh rate: {e.get_dbus_message()}")
        return False

    save_setting("refresh_rate", rate)
    return True

def get_screen_brightness() -> int | None:
    """Return the laptop screen brightness as a percentage (0-100), or None if unsupported"""
    value = get_property(POWER, POWER_PATH, SCREEN, "Brightness", session=True)
    if value is None or int(value) < 0:
        return None
    return int(value)


def set_screen_brightness(percent: int) -> bool:
    """Set the laptop screen brightness. Refuses values that would make the screen too dark to see"""
    if not MIN_SCREEN_BRIGHTNESS <= percent <= 100:
        print(f"Screen brightness must be between {MIN_SCREEN_BRIGHTNESS} and 100")
        return False
    return set_property(POWER, POWER_PATH, SCREEN, "Brightness", percent, session=True)


if __name__ == "__main__":
    print("Current mode:", get_current_mode())
    print("Rates:", get_refresh_rates())
    print("Current rate:", get_current_refresh_rate())
    print("Set 60:", set_refresh_rate(60))
    print("Rate now:", get_current_refresh_rate()) 
    print("Set 75:", set_refresh_rate(75))
    print("Set 144:", set_refresh_rate(144))
    print("Rate now:", get_current_refresh_rate())
