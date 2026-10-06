import dbus
import pytest

from asus_dashboard import dbus_helpers


class FakeObject:
    """Stands in for a D-Bus object that has the standard Get and Set methods"""

    def __init__(self):
        self.values = {"Percentage": 80}
        self.set_calls = []
        self.error = None

    def Get(self, interface, name):
        if self.error is not None:
            raise self.error
        return self.values[name]

    def Set(self, interface, name, value):
        if self.error is not None:
            raise self.error
        self.set_calls.append((interface, name, value))


class FakeBus:
    """Stands in for a bus connection. Hands out one object, or fails like a missing service"""

    def __init__(self, fake_object):
        self.fake_object = fake_object
        self.error = None

    def get_object(self, bus_name, path):
        if self.error is not None:
            raise self.error
        return self.fake_object


@pytest.fixture
def bus(monkeypatch):
    """Replace the bus connection and dbus.Interface, so the helpers talk to a fake object"""
    fake_bus = FakeBus(FakeObject())
    monkeypatch.setattr(dbus_helpers, "get_bus", lambda session: fake_bus)
    monkeypatch.setattr(dbus, "Interface", lambda obj, interface: obj)
    return fake_bus


def test_get_bus_picks_the_session_bus_only_when_asked(monkeypatch):
    monkeypatch.setattr(dbus, "SystemBus", lambda: "system bus")
    monkeypatch.setattr(dbus, "SessionBus", lambda: "session bus")
    assert dbus_helpers.get_bus(False) == "system bus"
    assert dbus_helpers.get_bus(True) == "session bus"


def test_get_property_returns_the_value(bus):
    assert dbus_helpers.get_property("name", "/path", "interface", "Percentage") == 80


def test_get_property_is_none_when_the_service_is_missing(bus, capsys):
    bus.error = dbus.exceptions.DBusException("The name is not activatable")
    assert dbus_helpers.get_property("name", "/path", "interface", "Percentage") is None
    assert "not activatable" in capsys.readouterr().out


def test_get_property_is_none_when_reading_fails(bus):
    bus.fake_object.error = dbus.exceptions.DBusException("No such property")
    assert dbus_helpers.get_property("name", "/path", "interface", "Banana") is None


def test_set_property_sends_the_value(bus):
    assert dbus_helpers.set_property("name", "/path", "interface", "ActiveProfile", "balanced") is True
    assert bus.fake_object.set_calls == [("interface", "ActiveProfile", "balanced")]


def test_set_property_is_false_when_the_service_refuses(bus, capsys):
    bus.fake_object.error = dbus.exceptions.DBusException("Invalid profile name 'turbo'")
    assert dbus_helpers.set_property("name", "/path", "interface", "ActiveProfile", "turbo") is False
    assert "Invalid profile name" in capsys.readouterr().out


def test_set_property_is_false_when_the_service_is_missing(bus):
    bus.error = dbus.exceptions.DBusException("The name is not activatable")
    assert dbus_helpers.set_property("name", "/path", "interface", "ActiveProfile", "balanced") is False
