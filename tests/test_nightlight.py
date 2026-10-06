import pytest

import nightlight
import settings
from nightlight import SCHEMA


@pytest.mark.parametrize("output, expected", [
    ("true", True),
    ("false", False),
])
def test_get_night_light_reads_on_and_off(fake_command, output, expected):
    fake_command.output = output
    assert nightlight.get_night_light() is expected
    assert fake_command.calls == [["gsettings", "get", SCHEMA, "night-light-enabled"]]


def test_get_night_light_is_none_when_gsettings_fails(fake_command):
    fake_command.output = None
    assert nightlight.get_night_light() is None


@pytest.mark.parametrize("output", ["uint32 2700", "2700"])
def test_get_night_light_temperature_reads_the_number(fake_command, output):
    fake_command.output = output
    assert nightlight.get_night_light_temperature() == 2700


def test_get_night_light_temperature_is_none_when_gsettings_fails(fake_command):
    fake_command.output = None
    assert nightlight.get_night_light_temperature() is None


def test_turning_night_light_on_sets_an_all_day_schedule_first(fake_command):
    assert nightlight.set_night_light(True) is True
    assert fake_command.calls == [
        ["gsettings", "set", SCHEMA, "night-light-schedule-automatic", "false"],
        ["gsettings", "set", SCHEMA, "night-light-schedule-from", "0.0"],
        ["gsettings", "set", SCHEMA, "night-light-schedule-to", "23.99"],
        ["gsettings", "set", SCHEMA, "night-light-enabled", "true"],
    ]
    assert settings.get_setting("night_light") is True


def test_turning_night_light_off_hands_the_schedule_back(fake_command):
    assert nightlight.set_night_light(False) is True
    assert fake_command.calls == [
        ["gsettings", "set", SCHEMA, "night-light-enabled", "false"],
        ["gsettings", "set", SCHEMA, "night-light-schedule-automatic", "true"],
    ]
    assert settings.get_setting("night_light") is False


def test_set_night_light_is_false_and_saves_nothing_if_a_command_fails(fake_command):
    fake_command.failing_word = "night-light-enabled"
    assert nightlight.set_night_light(True) is False
    assert settings.load_settings() == {}


def test_set_night_light_temperature_runs_the_command_and_saves(fake_command):
    assert nightlight.set_night_light_temperature(3000) is True
    assert fake_command.calls == [["gsettings", "set", SCHEMA, "night-light-temperature", "3000"]]
    assert settings.get_setting("night_light_temperature") == 3000


@pytest.mark.parametrize("kelvin", [1700, 4700])
def test_set_night_light_temperature_accepts_the_ends_of_the_range(fake_command, kelvin):
    assert nightlight.set_night_light_temperature(kelvin) is True


@pytest.mark.parametrize("kelvin", [1699, 4701, 0, 9000])
def test_set_night_light_temperature_refuses_out_of_range(fake_command, kelvin):
    assert nightlight.set_night_light_temperature(kelvin) is False
    assert fake_command.calls == []
    assert settings.load_settings() == {}


def test_set_night_light_temperature_saves_nothing_if_the_command_fails(fake_command):
    fake_command.output = None
    assert nightlight.set_night_light_temperature(3000) is False
    assert settings.load_settings() == {}
