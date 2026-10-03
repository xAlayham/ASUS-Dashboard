import dbus

PROPERTIES = "org.freedesktop.DBus.Properties"

def get_property(bus_name: str, path: str, interface: str, name: str):
    """Read one D-Bus property on the system bus or return None if it fails"""
    try:
        bus = dbus.SystemBus()
        obj = bus.get_object(bus_name, path)
        properties = dbus.Interface(obj, PROPERTIES)
        return properties.Get(interface, name)
    except dbus.exceptions.DBusException as e:
        print(f"D-Bus error reading {name}: {e.get_dbus_message()}")
        return None


def set_property(bus_name: str, path: str, interface: str, name: str, value) -> bool:
    """Write one D-Bus property on the system bus. Return True if it worked."""
    try:
        bus = dbus.SystemBus()
        obj = bus.get_object(bus_name, path)
        properties = dbus.Interface(obj, PROPERTIES)
        properties.Set(interface, name, value)
        return True
    except dbus.exceptions.DBusException as e:
        print(f"D-Bus error setting {name}: {e.get_dbus_message()}")
        return False