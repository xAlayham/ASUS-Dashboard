import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

PROFILES = "org.freedesktop.UPower.PowerProfiles"
PROFILES_PATH = "/org/freedesktop/UPOwer/PowerProfiles"
PROPERTIES = "org.freedesktop.DBus.Properties"

def on_properties_changed(interface, changed, invalidated):
    """Called by D-Bus everytime a property of the profile service changes"""
    if "ActiveProfile" in changed:
        profile = str(changed["ActiveProfile"])
        print(f"Profile changed to: {profile}", flush=True)

def main() -> None:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    bus.add_signal_receiver(
        on_properties_changed,
        signal_name="PropertiesChanged",
        dbus_interface=PROPERTIES,
        bus_name=PROFILES,
        path=PROFILES_PATH,
    )

    print("Watching the performance profile, Press Ctrl+C to stop.", flush=True)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()