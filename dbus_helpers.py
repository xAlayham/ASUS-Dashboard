import dbus

PROPERTIES = "org.freedesktop.DBus.Properties"


def get_bus(session: bool):
    """Return the session bus (desktop services) if session is True, otherwise the system bus"""
    return dbus.SessionBus() if session else dbus.SystemBus()


def get_property(bus_name: str, path: str, interface: str, name: str, session: bool = False):
    """Read one D-Bus property, or return None if it fails. Uses the system bus unless session is True"""
    try:
        obj = get_bus(session).get_object(bus_name, path)
        properties = dbus.Interface(obj, PROPERTIES)
        return properties.Get(interface, name)
    except dbus.exceptions.DBusException as e:
        print(f"D-Bus error reading {name}: {e.get_dbus_message()}")
        return None


def set_property(bus_name: str, path: str, interface: str, name: str, value, session: bool = False) -> bool:
    """Write one D-Bus property. Return True if it worked. Uses the system bus unless session is True"""
    try:
        obj = get_bus(session).get_object(bus_name, path)
        properties = dbus.Interface(obj, PROPERTIES)
        properties.Set(interface, name, value)
        return True
    except dbus.exceptions.DBusException as e:
        print(f"D-Bus error setting {name}: {e.get_dbus_message()}")
        return False
