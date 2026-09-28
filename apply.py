from settings import load_settings
from battery import set_charge_limit
from keyboard import set_keyboard_brightness

APPLIERS = {
    "charge_limit": set_charge_limit,
    "keyboard_brightness": set_keyboard_brightness
}

def apply_all() -> None:
    """Apply every saved setting to the hardware and print a summary"""
    settings = load_settings()
    if not settings:
        print("No saved settings, nothing to apply")
        return 

    applied = 0
    failed = 0
    for key, value in settings.items():
        applier = APPLIERS.get(key)
        if applier is None:
            print(f"Skipping unkown setting: {key}")
            continue
        ok = applier(value)
        if ok:
            applied += 1
        else:
            failed += 1
            
    print(f"Applied {applied} settings, {failed} failed")

if __name__ == "__main__":
    apply_all()