import os

import pytest

from asus_dashboard import status


def test_read_sysfs_strips_the_trailing_newline(tmp_path):
    (tmp_path / "value").write_text("balanced\n")
    assert status.read_sysfs(tmp_path / "value") == "balanced"


def test_read_sysfs_is_none_for_a_missing_file(tmp_path):
    assert status.read_sysfs(tmp_path / "missing") is None


def test_write_sysfs_writes_the_value(tmp_path):
    assert status.write_sysfs(tmp_path / "value", "3") is True
    assert (tmp_path / "value").read_text() == "3"


def test_write_sysfs_is_false_when_the_folder_is_missing(tmp_path):
    assert status.write_sysfs(tmp_path / "missing" / "value", "3") is False


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to read-only files")
def test_write_sysfs_is_false_without_permission(tmp_path):
    path = tmp_path / "value"
    path.write_text("1")
    path.chmod(0o444)
    assert status.write_sysfs(path, "3") is False
    assert path.read_text() == "1"


@pytest.mark.parametrize("value, maximum, expected", [
    ("50", "200", "25%"),
    ("96000", "96000", "100%"),
    ("2709000", "4110000", "66%"),
    ("0", "3", "0%"),
])
def test_percent_rounds_to_a_whole_number(tmp_path, value, maximum, expected):
    (tmp_path / "value").write_text(value + "\n")
    (tmp_path / "max").write_text(maximum + "\n")
    assert status.percent(tmp_path / "value", tmp_path / "max") == expected


def test_percent_is_not_supported_when_a_file_is_missing(tmp_path):
    (tmp_path / "value").write_text("50\n")
    assert status.percent(tmp_path / "value", tmp_path / "missing") == status.NOT_SUPPORTED


def test_percent_is_not_supported_when_the_maximum_is_zero(tmp_path):
    (tmp_path / "value").write_text("50\n")
    (tmp_path / "max").write_text("0\n")
    assert status.percent(tmp_path / "value", tmp_path / "max") == status.NOT_SUPPORTED


def test_find_hwmon_finds_a_folder_by_its_name(fake_hwmon):
    assert status.find_hwmon("asus") == fake_hwmon / "hwmon2"
    assert status.find_hwmon("coretemp") == fake_hwmon / "hwmon1"


def test_find_hwmon_is_none_for_an_unknown_name(fake_hwmon):
    assert status.find_hwmon("nvidia") is None


def test_find_hwmon_is_none_without_any_sensors():
    assert status.find_hwmon("asus") is None


def test_get_keyboard_shows_level_and_maximum(fake_keyboard):
    assert status.get_keyboard() == "2/3"


def test_get_charge_limit_shows_a_percentage(fake_battery):
    assert status.get_charge_limit() == "80%"


def test_status_getters_say_not_supported_without_hardware():
    assert status.get_keyboard() == status.NOT_SUPPORTED
    assert status.get_charge_limit() == status.NOT_SUPPORTED
    assert status.get_battery() == status.NOT_SUPPORTED
    assert status.get_fans() == status.NOT_SUPPORTED


def make_pci_device(folder, name, vendor, device_class):
    device = folder / name
    device.mkdir(parents=True)
    (device / "vendor").write_text(vendor + "\n")
    (device / "class").write_text(device_class + "\n")
    return device


@pytest.mark.parametrize("name", ["BAT0", "BAT1", "BATT"])
def test_find_battery_finds_the_battery_whatever_its_name(tmp_path, name):
    (tmp_path / "ACAD").mkdir()
    (tmp_path / name).mkdir()
    assert status.find_battery(tmp_path) == tmp_path / name


def test_find_battery_picks_the_first_of_several(tmp_path):
    (tmp_path / "BAT1").mkdir()
    (tmp_path / "BAT0").mkdir()
    assert status.find_battery(tmp_path) == tmp_path / "BAT0"


def test_find_battery_gives_a_missing_path_without_a_battery(tmp_path):
    (tmp_path / "ACAD").mkdir()
    battery = status.find_battery(tmp_path)
    assert not battery.exists()
    assert status.read_sysfs(battery / "capacity") is None


def test_find_nvidia_gpu_finds_the_card_at_any_address(tmp_path):
    make_pci_device(tmp_path, "0000:00:02.0", "0x8086", "0x030000")
    make_pci_device(tmp_path, "0000:02:00.0", "0x10de", "0x030200")
    assert status.find_nvidia_gpu(tmp_path) == tmp_path / "0000:02:00.0" / "power" / "runtime_status"


def test_find_nvidia_gpu_ignores_the_cards_sound_device(tmp_path):
    make_pci_device(tmp_path, "0000:01:00.1", "0x10de", "0x040300")
    assert not status.find_nvidia_gpu(tmp_path).exists()


def test_find_nvidia_gpu_ignores_other_makers(tmp_path):
    make_pci_device(tmp_path, "0000:00:02.0", "0x8086", "0x030000")
    make_pci_device(tmp_path, "0000:03:00.0", "0x1002", "0x030000")
    assert not status.find_nvidia_gpu(tmp_path).exists()


def test_find_nvidia_gpu_skips_devices_it_cannot_read(tmp_path):
    (tmp_path / "0000:00:00.0").mkdir()
    make_pci_device(tmp_path, "0000:01:00.0", "0x10de", "0x030000")
    assert status.find_nvidia_gpu(tmp_path).parent.parent.name == "0000:01:00.0"


def test_find_nvidia_gpu_gives_a_missing_path_without_any_devices(tmp_path):
    assert not status.find_nvidia_gpu(tmp_path).exists()
