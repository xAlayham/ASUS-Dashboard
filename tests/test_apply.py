import pytest

from asus_dashboard import apply
from asus_dashboard import settings


@pytest.fixture
def calls(monkeypatch):
    """Replace the real appliers with ones that record their calls. 'broken' always fails"""
    recorded = []

    def working(key):
        return lambda value: recorded.append((key, value)) or True

    appliers = {
        "charge_limit": working("charge_limit"),
        "profile": working("profile"),
        "night_light": working("night_light"),
        "broken": lambda value: False,
    }
    monkeypatch.setattr(apply, "APPLIERS", appliers)
    return recorded


def test_apply_all_says_so_when_nothing_is_saved(calls, capsys):
    apply.apply_all()
    assert "nothing to apply" in capsys.readouterr().out
    assert calls == []


def test_apply_all_applies_every_saved_setting(calls, capsys):
    settings.save_setting("charge_limit", 80)
    settings.save_setting("profile", "balanced")
    apply.apply_all()
    assert calls == [("charge_limit", 80), ("profile", "balanced")]
    assert "Applied 2 settings, 0 failed" in capsys.readouterr().out


def test_apply_all_counts_failures(calls, capsys):
    settings.save_setting("charge_limit", 80)
    settings.save_setting("broken", 1)
    apply.apply_all()
    assert "Applied 1 settings, 1 failed" in capsys.readouterr().out


def test_apply_all_skips_window_only_settings_silently(calls, capsys):
    settings.save_setting("theme", "Mocha")
    settings.save_setting("auto_switch", True)
    settings.save_setting("charge_limit", 80)
    apply.apply_all()
    output = capsys.readouterr().out
    assert calls == [("charge_limit", 80)]
    assert "Skipping" not in output
    assert "Applied 1 settings, 0 failed" in output


def test_apply_all_leaves_night_light_to_gnome(calls):
    settings.save_setting("night_light", True)
    apply.apply_all()
    assert calls == []


def test_apply_all_mentions_a_setting_it_does_not_know(calls, capsys):
    settings.save_setting("fan_colour", "red")
    apply.apply_all()
    assert "fan_colour" in capsys.readouterr().out


def test_window_only_settings_have_no_applier():
    for key in apply.UI_ONLY:
        assert key not in apply.APPLIERS
