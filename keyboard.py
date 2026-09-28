from status import read_sysfs, write_sysfs, KEYBOARD
from settings import save_setting

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

if __name__ == "__main__":
    print(set_keyboard_brightness(1))
    print(set_keyboard_brightness(5))
    print(set_keyboard_brightness(-1))

    current = read_sysfs(KEYBOARD / "brightness")
    print(f"Current brightness: {current}")
    
    print(set_keyboard_brightness(3))
        