from asus_dashboard.settings import load_settings
from asus_dashboard.battery import set_charge_limit
from asus_dashboard.keyboard import set_keyboard_brightness, apply_saved_keyboard_rgb
from asus_dashboard.nightlight import set_night_light, set_night_light_temperature
from asus_dashboard.performance import set_profile
from asus_dashboard.display import set_refresh_rate

APPLIERS = {
    "charge_limit": set_charge_limit,
    "keyboard_brightness": set_keyboard_brightness,
    "keyboard_rgb": apply_saved_keyboard_rgb,
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

def main() -> None:
    """Re-apply the saved settings. This is what the asus-dashboard-apply command runs"""
    apply_all()


if __name__ == "__main__":
    main()
