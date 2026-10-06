from settings import load_settings
from battery import set_charge_limit
from keyboard import set_keyboard_brightness
from nightlight import set_night_light, set_night_light_temperature
from performance import set_profile
from display import set_refresh_rate

APPLIERS = {
    "charge_limit": set_charge_limit,
    "keyboard_brightness": set_keyboard_brightness,
    "night_light": set_night_light,
    "night_light_temperature": set_night_light_temperature,
    "profile": set_profile,
    "refresh_rate": set_refresh_rate,
}

UI_ONLY = {"theme", "auto_switch", "charger_preset", "battery_preset"}
KEPT_BY_GNOME = {"night_light", "night_light_temperature"}

def apply_all() -> None:
    """Apply every saved setting to the hardware and print a summary"""
    settings = load_settings()
    if not settings:
        print("No saved settings, nothing to apply")
        return 

    applied = 0
    failed = 0
    for key, value in settings.items():
        if key in UI_ONLY or key in KEPT_BY_GNOME:
            continue
        applier = APPLIERS.get(key)
        if applier is None:
            print(f"Skipping unknown setting: {key}")
            continue
        ok = applier(value)
        if ok:
            applied += 1
        else:
            failed += 1
            
    print(f"Applied {applied} settings, {failed} failed")

if __name__ == "__main__":
    apply_all()