DEFAULT_CHARGER_PRESET = "Gaming"
DEFAULT_BATTERY_PRESET = "Battery saver"


def choose_preset(on_battery: bool, enabled: bool, charger_preset: str, battery_preset: str) -> str | None:
    """Decide which preset to switch to after the power source changed, or None to leave things alone.

    This only decides. It reads nothing and changes nothing, so it can be checked with plain values.
    """
    if not enabled:
        return None
    return battery_preset if on_battery else charger_preset


if __name__ == "__main__":
    print("Unplugged, automation on: ", choose_preset(True, True, DEFAULT_CHARGER_PRESET, DEFAULT_BATTERY_PRESET))
    print("Plugged in, automation on:", choose_preset(False, True, DEFAULT_CHARGER_PRESET, DEFAULT_BATTERY_PRESET))
    print("Unplugged, automation off:", choose_preset(True, False, DEFAULT_CHARGER_PRESET, DEFAULT_BATTERY_PRESET))
