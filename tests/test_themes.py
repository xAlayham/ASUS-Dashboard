import re
from pathlib import Path

import pytest

import asus_dashboard
from asus_dashboard.themes import DEFAULT_THEME, THEMES

STYLE_FILE = Path(asus_dashboard.__file__).parent / "style.qss"
PLACEHOLDERS = set(re.findall(r"@([A-Z0-9_]+)@", STYLE_FILE.read_text())) - {"ASSETS"}


def test_the_default_theme_exists():
    assert DEFAULT_THEME in THEMES


@pytest.mark.parametrize("name", list(THEMES))
def test_every_theme_defines_the_same_colours(name):
    assert set(THEMES[name]) == set(THEMES[DEFAULT_THEME])


@pytest.mark.parametrize("name", list(THEMES))
def test_every_placeholder_in_the_stylesheet_has_a_colour(name):
    assert PLACEHOLDERS - set(THEMES[name]) == set()


def test_the_stylesheet_uses_placeholders():
    assert "TEXT" in PLACEHOLDERS
    assert "ACCENT" in PLACEHOLDERS
