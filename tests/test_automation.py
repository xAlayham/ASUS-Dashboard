import pytest

from asus_dashboard import automation
from asus_dashboard.presets import PRESETS


@pytest.mark.parametrize("on_battery, expected", [
    (True, "Battery saver"),
    (False, "Gaming"),
])
def test_choose_preset_follows_the_power_source(on_battery, expected):
    assert automation.choose_preset(on_battery, True, "Gaming", "Battery saver") == expected


@pytest.mark.parametrize("on_battery", [True, False])
def test_choose_preset_does_nothing_when_switched_off(on_battery):
    assert automation.choose_preset(on_battery, False, "Gaming", "Battery saver") is None


def test_choose_preset_uses_whatever_presets_it_is_given():
    assert automation.choose_preset(True, True, "Balanced", "Silent") == "Silent"
    assert automation.choose_preset(False, True, "Balanced", "Silent") == "Balanced"


def test_the_default_presets_exist():
    assert automation.DEFAULT_CHARGER_PRESET in PRESETS
    assert automation.DEFAULT_BATTERY_PRESET in PRESETS
