import dbus
import pytest

from asus_dashboard import battery_info


@pytest.mark.parametrize("value, expected", [
    (79.6, 80),
    (79.4, 79),
    (100.0, 100),
    (0.0, 0),
])
def test_get_battery_percentage_rounds_to_a_whole_number(fake_properties, value, expected):
    fake_properties.values["Percentage"] = dbus.Double(value)
    percentage = battery_info.get_battery_percentage()
    assert percentage == expected
    assert type(percentage) is int


@pytest.mark.parametrize("code, name", list(battery_info.STATE_NAMES.items()))
def test_get_battery_state_names_each_code(fake_properties, code, name):
    fake_properties.values["State"] = dbus.UInt32(code)
    assert battery_info.get_battery_state() == name


def test_get_battery_state_is_unknown_for_a_new_code(fake_properties):
    fake_properties.values["State"] = dbus.UInt32(99)
    assert battery_info.get_battery_state() == "unknown"


def test_get_power_draw_rounds_to_one_decimal(fake_properties):
    fake_properties.values["EnergyRate"] = dbus.Double(14.237)
    assert battery_info.get_power_draw() == 14.2


@pytest.mark.parametrize("value", [True, False])
def test_is_on_battery_is_a_real_true_or_false(fake_properties, value):
    fake_properties.values["OnBattery"] = dbus.Boolean(value)
    assert battery_info.is_on_battery() is value


def test_battery_readings_are_none_without_the_service(fake_properties):
    assert battery_info.get_battery_percentage() is None
    assert battery_info.get_battery_state() is None
    assert battery_info.get_power_draw() is None
    assert battery_info.is_on_battery() is None
