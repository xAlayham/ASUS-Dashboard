import subprocess

import dbus
import pytest

import battery
import gpu
import keyboard
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
