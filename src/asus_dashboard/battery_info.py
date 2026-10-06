from pathlib import Path

from asus_dashboard.dbus_helpers import get_property
from asus_dashboard.status import BATTERY

UPOWER = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"


def battery_object_path(battery: Path) -> str:
    """Return the name UPower gives a battery, built from its folder name (BAT1 becomes battery_BAT1)"""
    return f"{UPOWER_PATH}/devices/battery_{battery.name}"


BATTERY_PATH = battery_object_path(BATTERY)
DEVICE = "org.freedesktop.UPower.Device"

STATE_NAMES = {
    1: "charging",
    2: "discharging",
    3: "empty",
    4: "fully charged",
    5: "plugged in, not charging",
    6: "pending discharge",
}

def get_battery_percentage() -> int | None:
    """Return the battery level as a whole percentage, or None"""
    value = get_property(UPOWER, BATTERY_PATH, DEVICE, "Percentage")
    if value is None:
        return None
    return round(float(value))

def get_battery_state() -> str | None:
    """Return the battery status in words, or None"""
    value = get_property(UPOWER, BATTERY_PATH, DEVICE, "State")
    if value is None:
        return None
    return STATE_NAMES.get(int(value), "unknown")

def get_power_draw() -> float | None:
    """Return how many watts are flowing in or out of the battetry, or None"""
    value = get_property(UPOWER, BATTERY_PATH, DEVICE, "EnergyRate")
    if value is None:
        return None
    return round(float(value), 1)

def is_on_battery() -> bool | None:
    """Return True if running o nbattery, False if plygged in, or None"""
    value = get_property(UPOWER, UPOWER_PATH, UPOWER, "OnBattery")
    if value is None:
        return None
    return bool(value)

if __name__ == "__main__":
    print("Battery:", get_battery_percentage(), "%")
    print("State:", get_battery_state())
    print("Power draw:", get_power_draw(), "W")
    print("On battery?", is_on_battery())
    print("Bad property:", get_property(UPOWER, BATTERY_PATH, DEVICE, "Banana"))