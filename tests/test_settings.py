import json

import settings


def test_load_settings_is_empty_before_anything_is_saved():
    assert settings.load_settings() == {}


def test_save_setting_can_be_read_back():
    settings.save_setting("charge_limit", 80)
    assert settings.load_settings() == {"charge_limit": 80}


def test_save_setting_creates_the_config_folder():
    assert not settings.CONFIG_DIR.exists()
    settings.save_setting("theme", "Mocha")
    assert settings.SETTINGS_FILE.exists()


def test_save_setting_keeps_the_other_settings():
    settings.save_setting("charge_limit", 80)
    settings.save_setting("keyboard_brightness", 3)
    assert settings.load_settings() == {"charge_limit": 80, "keyboard_brightness": 3}


def test_save_setting_replaces_an_existing_value():
    settings.save_setting("charge_limit", 80)
    settings.save_setting("charge_limit", 60)
    assert settings.load_settings() == {"charge_limit": 60}


def test_save_setting_keeps_each_type():
    settings.save_setting("number", 144)
    settings.save_setting("text", "performance")
    settings.save_setting("flag", False)
    settings.save_setting("group", {"effect": "Static", "colour": "#ff0000"})
    assert settings.load_settings() == {
        "number": 144,
        "text": "performance",
        "flag": False,
        "group": {"effect": "Static", "colour": "#ff0000"},
    }


def test_the_settings_file_is_readable_json():
    settings.save_setting("charge_limit", 80)
    text = settings.SETTINGS_FILE.read_text()
    assert json.loads(text) == {"charge_limit": 80}
    assert "\n" in text


def test_load_settings_ignores_a_damaged_file(capsys):
    settings.CONFIG_DIR.mkdir(parents=True)
    settings.SETTINGS_FILE.write_text("{ this is not json")
    assert settings.load_settings() == {}
    assert "damaged" in capsys.readouterr().out


def test_saving_after_a_damaged_file_starts_fresh():
    settings.CONFIG_DIR.mkdir(parents=True)
    settings.SETTINGS_FILE.write_text("{ this is not json")
    settings.save_setting("charge_limit", 80)
    assert settings.load_settings() == {"charge_limit": 80}


def test_get_setting_returns_the_saved_value():
    settings.save_setting("theme", "Teal")
    assert settings.get_setting("theme") == "Teal"


def test_get_setting_returns_none_when_missing():
    assert settings.get_setting("theme") is None


def test_get_setting_returns_the_default_when_missing():
    assert settings.get_setting("theme", "Mocha") == "Mocha"


def test_get_setting_prefers_a_saved_false_over_the_default():
    settings.save_setting("auto_switch", False)
    assert settings.get_setting("auto_switch", True) is False
