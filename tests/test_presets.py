import pytest

from asus_dashboard import presets
from asus_dashboard.apply import APPLIERS
from asus_dashboard.presets import PRESETS


class Recorder:
    """A stand-in applier that remembers what it was called with and returns a fixed answer"""

    def __init__(self, result: bool):
        self.result = result
        self.calls = []

    def __call__(self, value):
        self.calls.append(value)
        return self.result


@pytest.fixture
def fake_appliers(monkeypatch):
    """Replace the real appliers, so applying a preset changes nothing on the laptop"""
    appliers = {
        "profile": Recorder(True),
        "refresh_rate": Recorder(True),
        "keyboard_brightness": Recorder(True),
    }
    monkeypatch.setattr(presets, "APPLIERS", appliers)
    return appliers


@pytest.mark.parametrize("name", list(PRESETS))
def test_every_preset_setting_has_an_applier(name):
    for key in PRESETS[name]:
        assert key in APPLIERS


def test_no_two_presets_are_the_same():
    seen = []
    for preset in PRESETS.values():
        assert preset not in seen
        seen.append(preset)


@pytest.mark.parametrize("name", list(PRESETS))
def test_find_matching_preset_recognises_each_preset(name):
    assert presets.find_matching_preset(dict(PRESETS[name])) == name


def test_find_matching_preset_ignores_other_settings():
    state = dict(PRESETS["Silent"], charge_limit=80, theme="Mocha")
    assert presets.find_matching_preset(state) == "Silent"


def test_find_matching_preset_is_none_when_one_setting_differs():
    state = dict(PRESETS["Gaming"], keyboard_brightness=1)
    assert presets.find_matching_preset(state) is None


def test_find_matching_preset_is_none_when_a_setting_is_unknown():
    state = dict(PRESETS["Gaming"], refresh_rate=None)
    assert presets.find_matching_preset(state) is None


def test_find_matching_preset_is_none_for_an_empty_state():
    assert presets.find_matching_preset({}) is None


@pytest.mark.parametrize("name", list(PRESETS))
def test_describe_preset_mentions_every_value(name):
    text = presets.describe_preset(name)
    preset = PRESETS[name]
    assert preset["profile"] in text
    assert f"{preset['refresh_rate']} Hz" in text
    assert str(preset["keyboard_brightness"]) in text


def test_apply_preset_calls_each_applier_with_its_value(fake_appliers):
    assert presets.apply_preset("Battery saver") == (3, 0)
    assert fake_appliers["profile"].calls == ["power-saver"]
    assert fake_appliers["refresh_rate"].calls == [60]
    assert fake_appliers["keyboard_brightness"].calls == [0]


def test_apply_preset_counts_a_failure_and_still_applies_the_rest(fake_appliers):
    fake_appliers["refresh_rate"].result = False
    assert presets.apply_preset("Gaming") == (2, 1)
    assert fake_appliers["profile"].calls == ["performance"]
    assert fake_appliers["keyboard_brightness"].calls == [3]


def test_apply_preset_refuses_an_unknown_name(fake_appliers):
    assert presets.apply_preset("Turbo") == (0, 1)
    for applier in fake_appliers.values():
        assert applier.calls == []


def test_apply_preset_counts_a_setting_without_an_applier_as_failed(fake_appliers, monkeypatch):
    monkeypatch.setitem(presets.PRESETS, "Odd", {"profile": "balanced", "fan_colour": "red"})
    assert presets.apply_preset("Odd") == (1, 1)
