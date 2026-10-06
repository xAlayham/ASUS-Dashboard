import pytest

from asus_dashboard import battery
from asus_dashboard import settings


def read_limit(folder):
    return (folder / "charge_control_end_threshold").read_text()


def test_set_charge_limit_writes_and_saves(fake_battery):
    assert battery.set_charge_limit(60) is True
    assert read_limit(fake_battery) == "60"
    assert settings.get_setting("charge_limit") == 60


@pytest.mark.parametrize("limit", [20, 100])
def test_set_charge_limit_accepts_the_ends_of_the_range(fake_battery, limit):
    assert battery.set_charge_limit(limit) is True
    assert read_limit(fake_battery) == str(limit)


@pytest.mark.parametrize("limit", [19, 0, -5, 101, 1000])
def test_set_charge_limit_refuses_out_of_range(fake_battery, limit):
    assert battery.set_charge_limit(limit) is False
    assert read_limit(fake_battery) == "80\n"
    assert settings.load_settings() == {}


def test_set_charge_limit_is_false_and_saves_nothing_without_a_battery():
    assert battery.set_charge_limit(60) is False
    assert settings.load_settings() == {}


def test_get_charge_limit_value_is_a_number(fake_battery):
    assert battery.get_charge_limit_value() == 80


def test_get_charge_limit_value_is_none_without_a_battery():
    assert battery.get_charge_limit_value() is None
