import dbus
import pytest

from asus_dashboard import performance
from asus_dashboard import settings

PROFILES = [
    {"Profile": "power-saver", "Driver": "multiple"},
    {"Profile": "balanced", "Driver": "multiple"},
    {"Profile": "performance", "Driver": "multiple"},
]


@pytest.fixture
def profiles_service(fake_properties):
    """The fake power-profiles service, offering three profiles with 'balanced' active"""
    fake_properties.values["Profiles"] = PROFILES
    fake_properties.values["ActiveProfile"] = dbus.String("balanced")
    return fake_properties


def test_get_profile_choices_lists_the_profile_names(profiles_service):
    assert performance.get_profile_choices() == ["power-saver", "balanced", "performance"]


def test_get_profile_choices_is_empty_without_the_service(fake_properties):
    assert performance.get_profile_choices() == []


def test_get_profile_is_a_plain_string(profiles_service):
    profile = performance.get_profile()
    assert profile == "balanced"
    assert type(profile) is str


def test_get_profile_is_none_without_the_service(fake_properties):
    assert performance.get_profile() is None


def test_set_profile_asks_the_service_and_saves(profiles_service):
    assert performance.set_profile("performance") is True
    assert profiles_service.set_calls == [("ActiveProfile", "performance", False)]
    assert settings.get_setting("profile") == "performance"


@pytest.mark.parametrize("profile", ["turbo", "quiet", "", "Balanced"])
def test_set_profile_refuses_an_unknown_name_without_asking_the_service(profiles_service, profile):
    assert performance.set_profile(profile) is False
    assert profiles_service.set_calls == []
    assert settings.load_settings() == {}


def test_set_profile_saves_nothing_if_the_service_refuses(profiles_service):
    profiles_service.set_result = False
    assert performance.set_profile("performance") is False
    assert settings.load_settings() == {}


def test_set_profile_is_false_without_the_service(fake_properties):
    assert performance.set_profile("balanced") is False
    assert fake_properties.set_calls == []
