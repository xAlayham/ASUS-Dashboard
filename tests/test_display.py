import dbus
import pytest

import display
import settings


def test_get_modes_turns_each_mode_into_a_simple_dict(fake_display):
    assert display.get_modes() == [
        {"id": "1920x1080@144.003", "width": 1920, "height": 1080, "rate": 144, "current": True},
        {"id": "1920x1080@60.004", "width": 1920, "height": 1080, "rate": 60, "current": False},
        {"id": "1680x1050@144.003", "width": 1680, "height": 1050, "rate": 144, "current": False},
    ]


def test_get_modes_picks_the_laptop_screen_when_another_is_listed_first(fake_display):
    fake_display.monitors.insert(0, (("HDMI-1", "DEL", "0x1", "0x0"), [], {}))
    assert len(display.get_modes()) == 3


def test_get_modes_is_empty_without_a_laptop_screen(fake_display):
    fake_display.monitors.clear()
    fake_display.add_monitor("HDMI-1", [("3840x2160@60.000", 3840, 2160, 60.0, True)])
    assert display.get_modes() == []


def test_get_modes_is_empty_without_the_display_service(monkeypatch):
    monkeypatch.setattr(display, "get_display_config", lambda: None)
    assert display.get_modes() == []


def test_get_display_state_is_none_when_reading_fails(fake_display):
    fake_display.read_error = dbus.exceptions.DBusException("service busy")
    assert display.get_display_state() is None


def test_get_current_mode_is_the_one_marked_current(fake_display):
    assert display.get_current_mode()["id"] == "1920x1080@144.003"


def test_get_current_mode_is_none_when_nothing_is_marked(fake_display):
    fake_display.monitors.clear()
    fake_display.add_monitor("eDP-1", [("1920x1080@60.004", 1920, 1080, 60.004, False)])
    assert display.get_current_mode() is None


def test_get_refresh_rates_lists_only_the_current_resolution(fake_display):
    assert display.get_refresh_rates() == [144, 60]


def test_get_refresh_rates_lists_each_rate_once(fake_display):
    fake_display.monitors.clear()
    fake_display.add_monitor("eDP-1", [
        ("1920x1080@144.003", 1920, 1080, 144.003, True),
        ("1920x1080@144.001", 1920, 1080, 144.001, False),
        ("1920x1080@60.004", 1920, 1080, 60.004, False),
    ])
    assert display.get_refresh_rates() == [144, 60]


def test_get_current_refresh_rate_is_a_whole_number(fake_display):
    assert display.get_current_refresh_rate() == 144


def test_refresh_rate_readings_are_empty_without_the_display_service(monkeypatch):
    monkeypatch.setattr(display, "get_display_config", lambda: None)
    assert display.get_refresh_rates() == []
    assert display.get_current_refresh_rate() is None


def test_set_refresh_rate_applies_the_matching_mode_and_saves(fake_display):
    assert display.set_refresh_rate(60) is True
    layout = (0, 0, 1.0, 0, True, [("eDP-1", "1920x1080@60.004", {})])
    assert fake_display.applied == [(7, display.TEMPORARY, [layout], {})]
    assert settings.get_setting("refresh_rate") == 60


def test_set_refresh_rate_keeps_the_scale_and_position(fake_display):
    fake_display.logical_monitors = [(100, 50, 1.25, 0, True, [], {})]
    assert display.set_refresh_rate(60) is True
    applied_layout = fake_display.applied[0][2][0]
    assert applied_layout[:5] == (100, 50, 1.25, 0, True)


@pytest.mark.parametrize("rate", [75, 0, 120, -60])
def test_set_refresh_rate_refuses_a_rate_the_screen_does_not_have(fake_display, rate):
    assert display.set_refresh_rate(rate) is False
    assert fake_display.applied == []
    assert settings.load_settings() == {}


def test_set_refresh_rate_refuses_when_an_external_monitor_is_connected(fake_display):
    fake_display.add_monitor("HDMI-1", [("3840x2160@60.000", 3840, 2160, 60.0, True)])
    assert display.set_refresh_rate(60) is False
    assert fake_display.applied == []
    assert settings.load_settings() == {}


def test_set_refresh_rate_saves_nothing_if_gnome_rejects_it(fake_display):
    fake_display.apply_error = dbus.exceptions.DBusException("Invalid mode")
    assert display.set_refresh_rate(60) is False
    assert settings.load_settings() == {}


def test_get_screen_brightness_is_a_number(fake_properties):
    fake_properties.values["Brightness"] = dbus.Int32(70)
    assert display.get_screen_brightness() == 70
    assert fake_properties.get_calls == [("Brightness", True)]


@pytest.mark.parametrize("value", [None, dbus.Int32(-1)])
def test_get_screen_brightness_is_none_when_unsupported(fake_properties, value):
    fake_properties.values["Brightness"] = value
    assert display.get_screen_brightness() is None


def test_set_screen_brightness_asks_the_session_service(fake_properties):
    assert display.set_screen_brightness(50) is True
    assert fake_properties.set_calls == [("Brightness", 50, True)]


@pytest.mark.parametrize("percent", [display.MIN_SCREEN_BRIGHTNESS, 100])
def test_set_screen_brightness_accepts_the_ends_of_the_range(fake_properties, percent):
    assert display.set_screen_brightness(percent) is True


@pytest.mark.parametrize("percent", [0, 4, 101, -10])
def test_set_screen_brightness_refuses_out_of_range(fake_properties, percent):
    assert display.set_screen_brightness(percent) is False
    assert fake_properties.set_calls == []


def test_set_screen_brightness_is_false_if_the_service_refuses(fake_properties):
    fake_properties.set_result = False
    assert display.set_screen_brightness(50) is False
