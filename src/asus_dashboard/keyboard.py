from asus_dashboard.status import read_sysfs, write_sysfs, KEYBOARD
from asus_dashboard.settings import get_setting, save_setting

RGB_EFFECTS = {
    "Static": 0,
    "Breathing": 1,
    "Colour cycle": 2,
    "Strobing": 10,
}
RGB_SPEEDS = {
    "Slow": 0,
    "Medium": 1,
    "Fast": 2,
}
EFFECTS_WITH_COLOUR = {"Static", "Breathing", "Strobing"}
EFFECTS_WITH_SPEED = {"Breathing", "Colour cycle"}
DEFAULT_RGB = {"effect": "Static", "colour": "#ff0000", "speed": "Medium"}
SAVE_TO_KEYBOARD = 1
HEX_DIGITS = "0123456789abcdefABCDEF"

def set_keyboard_brightness(level: int) -> bool:
    """Switch the keyboard brightness level, only if the input is valid"""
    raw_maximum = read_sysfs(KEYBOARD / "max_brightness")
    if raw_maximum is None:
        print("Keyboard brightness not supported")
        return False

    maximum = int(raw_maximum)
    if level < 0 or level > maximum:
        print(f"Brightness must be between 0 and {maximum}")
        return False
    
    ok = write_sysfs(KEYBOARD / "brightness", str(level))
    if ok:
        save_setting("keyboard_brightness", level)
        print(f"Saved keyboard brightness to: {level}")
    return ok

def get_keyboard_brightness() -> int | None:
    """Return the keyboard backlight level (0-3), or None if unsupported"""
    value = read_sysfs(KEYBOARD / "brightness")
    if value is None:
        return None
    return int(value)

def parse_colour(colour: str) -> tuple[int, int, int] | None:
    """Turn a colour like '#ff8800' into (red, green, blue) numbers from 0 to 255, or None if it is not valid"""
    if len(colour) != 7 or not colour.startswith("#"):
        return None
    if not all(character in HEX_DIGITS for character in colour[1:]):
        return None
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def set_keyboard_rgb(effect: str, colour: str, speed: str) -> bool:
    """Set the keyboard lighting effect, colour and speed, and remember them.

    The keyboard cannot be asked what it is showing, so the choice is saved in settings and that
    saved copy is what the dashboard displays.
    """
    if effect not in RGB_EFFECTS:
        print(f"'{effect}' is not a valid effect. Choices: {', '.join(RGB_EFFECTS)}")
        return False
    if speed not in RGB_SPEEDS:
        print(f"'{speed}' is not a valid speed. Choices: {', '.join(RGB_SPEEDS)}")
        return False
    rgb = parse_colour(colour)
    if rgb is None:
        print(f"'{colour}' is not a valid colour. Use the form #rrggbb")
        return False

    red, green, blue = rgb
    command = f"{SAVE_TO_KEYBOARD} {RGB_EFFECTS[effect]} {red} {green} {blue} {RGB_SPEEDS[speed]}"
    ok = write_sysfs(KEYBOARD / "kbd_rgb_mode", command)
    if ok:
        save_setting("keyboard_rgb", {"effect": effect, "colour": colour, "speed": speed})
    return ok


def get_keyboard_rgb() -> dict:
    """Return the remembered effect, colour and speed, with defaults for anything missing or invalid"""
    saved = get_setting("keyboard_rgb", {})
    result = DEFAULT_RGB.copy()
    if not isinstance(saved, dict):
        return result
    if saved.get("effect") in RGB_EFFECTS:
        result["effect"] = saved["effect"]
    if isinstance(saved.get("colour"), str) and parse_colour(saved["colour"]) is not None:
        result["colour"] = saved["colour"]
    if saved.get("speed") in RGB_SPEEDS:
        result["speed"] = saved["speed"]
    return result


def apply_saved_keyboard_rgb(saved: dict) -> bool:
    """Apply a saved {'effect', 'colour', 'speed'} dict. Used when settings are re-applied at login"""
    if not isinstance(saved, dict):
        print("Saved keyboard lighting is not valid")
        return False
    return set_keyboard_rgb(saved.get("effect", ""), saved.get("colour", ""), saved.get("speed", ""))


if __name__ == "__main__":
    print(set_keyboard_brightness(1))
    print(set_keyboard_brightness(5))
    print(set_keyboard_brightness(-1))

    current = read_sysfs(KEYBOARD / "brightness")
    print(f"Current brightness: {current}")
    
    print(set_keyboard_brightness(3))
        