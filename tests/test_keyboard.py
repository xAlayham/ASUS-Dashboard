import pytest

from asus_dashboard import keyboard
from asus_dashboard import settings


def test_set_keyboard_brightness_writes_and_saves(fake_keyboard):
    assert keyboard.set_keyboard_brightness(1) is True
    assert (fake_keyboard / "brightness").read_text() == "1"
    assert settings.get_setting("keyboard_brightness") == 1


@pytest.mark.parametrize("level", [0, 3])
def test_set_keyboard_brightness_accepts_the_ends_of_the_range(fake_keyboard, level):
    assert keyboard.set_keyboard_brightness(level) is True


@pytest.mark.parametrize("level", [-1, 4, 99])
def test_set_keyboard_brightness_refuses_out_of_range(fake_keyboard, level):
    assert keyboard.set_keyboard_brightness(level) is False
    assert (fake_keyboard / "brightness").read_text() == "2\n"
    assert settings.load_settings() == {}


def test_set_keyboard_brightness_uses_the_maximum_the_keyboard_reports(fake_keyboard):
    (fake_keyboard / "max_brightness").write_text("1\n")
    assert keyboard.set_keyboard_brightness(1) is True
    assert keyboard.set_keyboard_brightness(2) is False


def test_set_keyboard_brightness_is_false_without_a_keyboard_light():
    assert keyboard.set_keyboard_brightness(1) is False
    assert settings.load_settings() == {}


def test_get_keyboard_brightness_is_a_number(fake_keyboard):
    assert keyboard.get_keyboard_brightness() == 2


def test_get_keyboard_brightness_is_none_without_a_keyboard_light():
    assert keyboard.get_keyboard_brightness() is None


@pytest.mark.parametrize("colour, expected", [
    ("#ff8800", (255, 136, 0)),
    ("#000000", (0, 0, 0)),
    ("#ffffff", (255, 255, 255)),
    ("#00AAFF", (0, 170, 255)),
])
def test_parse_colour_reads_hex_colours(colour, expected):
    assert keyboard.parse_colour(colour) == expected


@pytest.mark.parametrize("colour", [
    "red",
    "",
    "#fff",
    "ff8800",
    "ff8800ff",
    "#gggggg",
    "#ff88 0",
    "#-1-1-1",
    "#+f+f+f",
])
def test_parse_colour_is_none_for_anything_else(colour):
    assert keyboard.parse_colour(colour) is None


def test_set_keyboard_rgb_writes_the_command_and_saves(fake_keyboard):
    assert keyboard.set_keyboard_rgb("Breathing", "#00aaff", "Fast") is True
    assert (fake_keyboard / "kbd_rgb_mode").read_text() == "1 1 0 170 255 2"
    assert settings.get_setting("keyboard_rgb") == {"effect": "Breathing", "colour": "#00aaff", "speed": "Fast"}


@pytest.mark.parametrize("effect, number", [
    ("Static", 0),
    ("Breathing", 1),
    ("Colour cycle", 2),
    ("Strobing", 10),
])
def test_set_keyboard_rgb_sends_the_number_for_each_effect(fake_keyboard, effect, number):
    assert keyboard.set_keyboard_rgb(effect, "#ff0000", "Slow") is True
    assert (fake_keyboard / "kbd_rgb_mode").read_text() == f"1 {number} 255 0 0 0"


@pytest.mark.parametrize("effect, colour, speed", [
    ("Disco", "#ff0000", "Medium"),
    ("Static", "red", "Medium"),
    ("Static", "#ff0000", "Warp"),
    ("", "", ""),
])
def test_set_keyboard_rgb_refuses_invalid_choices(fake_keyboard, effect, colour, speed):
    assert keyboard.set_keyboard_rgb(effect, colour, speed) is False
    assert (fake_keyboard / "kbd_rgb_mode").read_text() == ""
    assert settings.load_settings() == {}


def test_set_keyboard_rgb_is_false_and_saves_nothing_without_a_keyboard_light():
    assert keyboard.set_keyboard_rgb("Static", "#ff0000", "Medium") is False
    assert settings.load_settings() == {}


def test_get_keyboard_rgb_gives_defaults_when_nothing_is_saved():
    assert keyboard.get_keyboard_rgb() == keyboard.DEFAULT_RGB


def test_get_keyboard_rgb_does_not_hand_out_the_defaults_themselves():
    keyboard.get_keyboard_rgb()["effect"] = "changed"
    assert keyboard.DEFAULT_RGB["effect"] == "Static"


def test_get_keyboard_rgb_returns_what_was_saved():
    saved = {"effect": "Strobing", "colour": "#123456", "speed": "Slow"}
    settings.save_setting("keyboard_rgb", saved)
    assert keyboard.get_keyboard_rgb() == saved


def test_get_keyboard_rgb_replaces_only_the_invalid_parts():
    settings.save_setting("keyboard_rgb", {"effect": "Disco", "colour": "#123456", "speed": "Warp"})
    assert keyboard.get_keyboard_rgb() == {"effect": "Static", "colour": "#123456", "speed": "Medium"}


@pytest.mark.parametrize("saved", ["nonsense", 5, True, {"colour": 12}])
def test_get_keyboard_rgb_survives_damaged_saved_data(saved):
    settings.save_setting("keyboard_rgb", saved)
    assert keyboard.get_keyboard_rgb() == keyboard.DEFAULT_RGB


def test_apply_saved_keyboard_rgb_applies_a_saved_choice(fake_keyboard):
    saved = {"effect": "Static", "colour": "#00ff00", "speed": "Medium"}
    assert keyboard.apply_saved_keyboard_rgb(saved) is True
    assert (fake_keyboard / "kbd_rgb_mode").read_text() == "1 0 0 255 0 1"


@pytest.mark.parametrize("saved", ["nonsense", 5, {}, {"effect": "Static"}])
def test_apply_saved_keyboard_rgb_refuses_damaged_saved_data(fake_keyboard, saved):
    assert keyboard.apply_saved_keyboard_rgb(saved) is False
    assert (fake_keyboard / "kbd_rgb_mode").read_text() == ""
