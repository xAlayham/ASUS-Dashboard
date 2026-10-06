import subprocess

import dbus
import pytest

import battery
import battery_info
import display
import gpu
import keyboard
import nightlight
import performance
import sensors
import settings
import status

HARDWARE_PATHS = [
    (status, "PROFILE"),
    (status, "ARMOURY"),
    (status, "NVIDIA_GPU"),
    (status, "SCREEN"),
    (status, "KEYBOARD"),
    (status, "BATTERY"),
    (status, "HWMON"),
    (battery, "BATTERY"),
    (keyboard, "KEYBOARD"),
    (sensors, "BATTERY"),
    (sensors, "PROC_STAT"),
    (gpu, "NVIDIA_GPU"),
]


def refuse(*args, **kwargs):
    """Stands in for anything that would reach the real system, and fails the test loudly instead"""
    raise AssertionError("A test tried to run a real command or use the real D-Bus")


@pytest.fixture(autouse=True)
def isolated_system(tmp_path, monkeypatch):
    """Runs for every test automatically, so no test can touch the real laptop.

    The settings file moves to a temporary folder, every hardware path points at a folder that
    does not exist, and running a command or opening D-Bus fails the test.
    """
    config_dir = tmp_path / "config"
    monkeypatch.setattr(settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(settings, "SETTINGS_FILE", config_dir / "settings.json")

    missing = tmp_path / "no-such-hardware"
    for module, name in HARDWARE_PATHS:
        monkeypatch.setattr(module, name, missing / name.lower())

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(dbus, "SystemBus", refuse)
    monkeypatch.setattr(dbus, "SessionBus", refuse)


@pytest.fixture
def fake_battery(tmp_path, monkeypatch):
    """A pretend battery folder: limit 80, discharging at 1.5 A and 12 V"""
    folder = tmp_path / "BAT1"
    folder.mkdir()
    (folder / "charge_control_end_threshold").write_text("80\n")
    (folder / "status").write_text("Discharging\n")
    (folder / "current_now").write_text("1500000\n")
    (folder / "voltage_now").write_text("12000000\n")
    for module in (status, battery, sensors):
        monkeypatch.setattr(module, "BATTERY", folder)
    return folder


@pytest.fixture
def fake_keyboard(tmp_path, monkeypatch):
    """A pretend keyboard light folder: brightness 2 of 3, with an empty lighting-effect file"""
    folder = tmp_path / "kbd_backlight"
    folder.mkdir()
    (folder / "brightness").write_text("2\n")
    (folder / "max_brightness").write_text("3\n")
    (folder / "kbd_rgb_mode").write_text("")
    for module in (status, keyboard):
        monkeypatch.setattr(module, "KEYBOARD", folder)
    return folder


@pytest.fixture
def fake_hwmon(tmp_path, monkeypatch):
    """A pretend sensors folder: CPU at 56 °C, CPU fan at 3100 RPM, GPU fan stopped"""
    folder = tmp_path / "hwmon"
    sensors_by_folder = {
        "hwmon0": {"name": "acpitz"},
        "hwmon1": {"name": "coretemp", "temp1_input": "56000"},
        "hwmon2": {"name": "asus", "fan1_input": "3100", "fan2_input": "0"},
    }
    for folder_name, files in sensors_by_folder.items():
        (folder / folder_name).mkdir(parents=True)
        for file_name, content in files.items():
            (folder / folder_name / file_name).write_text(content + "\n")
    monkeypatch.setattr(status, "HWMON", folder)
    return folder


class FakeCommand:
    """Stands in for run_command: remembers every command and returns what the test chose"""

    def __init__(self):
        self.output = ""
        self.failing_word = None
        self.calls = []
        self.timeouts = []

    def __call__(self, args, timeout=5):
        self.calls.append(args)
        self.timeouts.append(timeout)
        if self.failing_word is not None and self.failing_word in args:
            return None
        return self.output


class FakeProperties:
    """Stands in for the D-Bus helpers: answers from a dict and remembers every write"""

    def __init__(self):
        self.values = {}
        self.set_result = True
        self.get_calls = []
        self.set_calls = []

    def get(self, bus_name, path, interface, name, session=False):
        self.get_calls.append((name, session))
        return self.values.get(name)

    def set(self, bus_name, path, interface, name, value, session=False):
        self.set_calls.append((name, value, session))
        return self.set_result


class FakeDisplayConfig:
    """Stands in for GNOME's display service: one screen setup to read, and a record of what was applied"""

    def __init__(self):
        self.serial = 7
        self.monitors = []
        self.logical_monitors = [(0, 0, 1.0, 0, True, [], {})]
        self.read_error = None
        self.apply_error = None
        self.applied = []

    def add_monitor(self, connector, modes):
        """Add a screen. Each mode is (id, width, height, rate, is_current)"""
        converted = []
        for mode_id, width, height, rate, is_current in modes:
            flags = {"is-current": True} if is_current else {}
            converted.append((mode_id, width, height, rate, 1.0, [1.0, 2.0], flags))
        self.monitors.append(((connector, "CMN", "0x1521", "0x0"), converted, {}))

    def GetCurrentState(self):
        if self.read_error is not None:
            raise self.read_error
        return self.serial, self.monitors, self.logical_monitors, {}

    def ApplyMonitorsConfig(self, serial, method, logical_monitors, properties):
        if self.apply_error is not None:
            raise self.apply_error
        self.applied.append((serial, method, logical_monitors, properties))


@pytest.fixture
def fake_command(monkeypatch):
    """Replace run_command in every module that uses it, so no real program is started"""
    fake = FakeCommand()
    for module in (nightlight, gpu):
        monkeypatch.setattr(module, "run_command", fake)
    return fake


@pytest.fixture
def fake_properties(monkeypatch):
    """Replace the D-Bus property helpers in every module that uses them"""
    fake = FakeProperties()
    for module in (performance, battery_info, gpu, display):
        monkeypatch.setattr(module, "get_property", fake.get)
    for module in (performance, display):
        monkeypatch.setattr(module, "set_property", fake.set)
    return fake


@pytest.fixture
def fake_display(monkeypatch):
    """A pretend laptop screen at 1920x1080: 144 Hz now, 60 Hz available, plus a smaller 144 Hz mode"""
    fake = FakeDisplayConfig()
    fake.add_monitor("eDP-1", [
        ("1920x1080@144.003", 1920, 1080, 144.003, True),
        ("1920x1080@60.004", 1920, 1080, 60.004, False),
        ("1680x1050@144.003", 1680, 1050, 144.003, False),
    ])
    monkeypatch.setattr(display, "get_display_config", lambda: fake)
    return fake
