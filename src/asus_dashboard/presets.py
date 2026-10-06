from asus_dashboard.apply import APPLIERS

PRESETS = {
    "Gaming": {"profile": "performance", "refresh_rate": 144, "keyboard_brightness": 3},
    "Balanced": {"profile": "balanced", "refresh_rate": 144, "keyboard_brightness": 2},
    "Silent": {"profile": "power-saver", "refresh_rate": 144, "keyboard_brightness": 2},
    "Battery saver": {"profile": "power-saver", "refresh_rate": 60, "keyboard_brightness": 0},
}


def apply_preset(name: str) -> tuple[int, int]:
    """Apply every setting of one preset. Return (how many worked, how many failed).

    An unknown preset name, or a setting that has no applier, counts as a failure.
    One failed setting does not stop the others from being applied.
    """
    if name not in PRESETS:
        print(f"'{name}' is not a preset. Choices: {', '.join(PRESETS)}")
        return 0, 1

    applied = 0
    failed = 0
    for key, value in PRESETS[name].items():
        applier = APPLIERS.get(key)
        if applier is None:
            print(f"Preset '{name}' has an unknown setting: {key}")
            failed += 1
        elif applier(value):
            applied += 1
        else:
            failed += 1
    return applied, failed


def describe_preset(name: str) -> str:
    """Return one line saying what a preset sets, e.g. 'performance power mode · 144 Hz · keyboard light 3'"""
    preset = PRESETS[name]
    return f"{preset['profile']} power mode  ·  {preset['refresh_rate']} Hz  ·  keyboard light {preset['keyboard_brightness']}"


def find_matching_preset(state: dict) -> str | None:
    """Return the name of the preset whose settings all equal the given state, or None if none match"""
    for name, preset in PRESETS.items():
        if all(state.get(key) == value for key, value in preset.items()):
            return name
    return None


if __name__ == "__main__":
    for preset_name in PRESETS:
        print(f"{preset_name}: {describe_preset(preset_name)}")
