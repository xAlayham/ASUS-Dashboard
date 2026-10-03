from dbus_helpers import get_property, set_property
from settings import save_setting

BUS_NAME = "org.freedesktop.UPower.PowerProfiles"
OBJECT_PATH = "/org/freedesktop/UPower/PowerProfiles"
INTERFACE = "org.freedesktop.UPower.PowerProfiles"

def get_profile_choices() -> list[str]:
    """Return the profiels this laptop supports, or an empty list if none"""
    profiles = get_property(BUS_NAME, OBJECT_PATH, INTERFACE, "Profiles")
    if profiles is None:
        return []
    return [str(entry["Profile"]) for entry in profiles]

def get_profile() -> str | None:
    """Return current active profile as a string, or None"""
    active_profile = get_property(BUS_NAME, OBJECT_PATH, INTERFACE, "ActiveProfile")
    if active_profile is None:
        return None
    return str(active_profile)

def set_profile(profile: str) -> bool:
    """Switch the performance profile, but only if the name is valid."""
    choices = get_profile_choices()
    if profile not in choices:
        print(f"'{profile}' is not a valid profile. Choices: {', '.join(choices)}")
        return False

    if not set_property(BUS_NAME, OBJECT_PATH, INTERFACE, "ActiveProfile", profile):
        return False

    save_setting("profile", profile)
    return True

if __name__ == "__main__":
    from pathlib import Path
    from status import read_sysfs

    print("Choices:", get_profile_choices())
    print("Current:", get_profile())

    print("\nTrying 'turbo'...")
    set_profile("turbo")

    print("\nSetting 'power-saver'...")
    set_profile("power-saver")
    print("Current:", get_profile())
    print("Kernel says:", read_sysfs(Path("/sys/firmware/acpi/platform_profile")))

    print("\nSetting 'performance' again...")
    set_profile("performance")
    print("Current:", get_profile())