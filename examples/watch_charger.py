import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
 
from asus_dashboard.performance import set_profile

UPOWER = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
PROPERTIES = "org.freedesktop.DBus.Properties"
 
ON_BATTERY_PROFILE = "power-saver"
ON_AC_PROFILE = "performance"

def on_properties_changed(interface, changed, invalidated):
    """Called by D-Bus every time a UPower property changes"""
    if "OnBattery" not in changed:
        return
 
    if bool(changed["OnBattery"]):
        print("Charger unplugged", flush=True)
        set_profile(ON_BATTERY_PROFILE)
    else:
        print("Charger plugged in", flush=True)
        set_profile(ON_AC_PROFILE)

def main() -> None:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    bus.add_signal_receiver(
        on_properties_changed,
        signal_name="PropertiesChanged",
        dbus_interface=PROPERTIES,
        bus_name=UPOWER,
        path=UPOWER_PATH,
    )

    print("Watching the charger. Press Ctrl+C to stop.", flush=True)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()