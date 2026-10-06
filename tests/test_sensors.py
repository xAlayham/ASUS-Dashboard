import pytest

from asus_dashboard import sensors


@pytest.fixture
def proc_stat(tmp_path, monkeypatch):
    """A pretend /proc/stat, with a helper to write the CPU line"""
    path = tmp_path / "stat"
    monkeypatch.setattr(sensors, "PROC_STAT", path)

    def write(user: int, idle: int, iowait: int = 0):
        path.write_text(f"cpu  {user} 0 0 {idle} {iowait} 0 0 0 0 0\ncpu0 1 2 3 4 5 6 7 8 9 10\n")

    return write


def test_read_cpu_times_adds_up_the_first_line(proc_stat):
    proc_stat(user=150, idle=800, iowait=50)
    assert sensors.read_cpu_times() == (1000, 850)


def test_read_cpu_times_is_none_when_unreadable():
    assert sensors.read_cpu_times() is None


def test_cpu_usage_is_the_busy_share_between_two_readings(proc_stat):
    proc_stat(user=100, idle=900)
    usage = sensors.CpuUsage()
    proc_stat(user=350, idle=1650)
    assert usage.read() == pytest.approx(25.0)


def test_cpu_usage_counts_waiting_for_the_disk_as_idle(proc_stat):
    proc_stat(user=0, idle=1000)
    usage = sensors.CpuUsage()
    proc_stat(user=0, idle=1500, iowait=500)
    assert usage.read() == pytest.approx(0.0)


def test_cpu_usage_compares_with_the_previous_reading_each_time(proc_stat):
    proc_stat(user=0, idle=1000)
    usage = sensors.CpuUsage()
    proc_stat(user=1000, idle=1000)
    assert usage.read() == pytest.approx(100.0)
    proc_stat(user=1000, idle=2000)
    assert usage.read() == pytest.approx(0.0)


def test_cpu_usage_is_none_when_no_time_has_passed(proc_stat):
    proc_stat(user=100, idle=900)
    usage = sensors.CpuUsage()
    assert usage.read() is None


def test_cpu_usage_is_none_when_unreadable():
    assert sensors.CpuUsage().read() is None


def test_cpu_usage_recovers_after_an_unreadable_reading(proc_stat, tmp_path):
    usage = sensors.CpuUsage()
    proc_stat(user=100, idle=900)
    assert usage.read() is None
    proc_stat(user=600, idle=1400)
    assert usage.read() == pytest.approx(50.0)


def test_get_power_draw_multiplies_current_and_voltage(fake_battery):
    assert sensors.get_power_draw() == pytest.approx(18.0)


@pytest.mark.parametrize("state", ["Charging", "Full", "Not charging"])
def test_get_power_draw_is_none_unless_discharging(fake_battery, state):
    (fake_battery / "status").write_text(state + "\n")
    assert sensors.get_power_draw() is None


def test_get_power_draw_is_none_when_a_reading_is_missing(fake_battery):
    (fake_battery / "current_now").unlink()
    assert sensors.get_power_draw() is None


def test_get_power_draw_is_none_without_a_battery():
    assert sensors.get_power_draw() is None


def test_get_cpu_temperature_converts_millidegrees(fake_hwmon):
    assert sensors.get_cpu_temperature() == pytest.approx(56.0)


def test_get_fan_speeds_gives_cpu_then_gpu(fake_hwmon):
    assert sensors.get_fan_speeds() == (3100, 0)


def test_get_fan_speeds_is_none_when_one_fan_is_missing(fake_hwmon):
    (fake_hwmon / "hwmon2" / "fan2_input").unlink()
    assert sensors.get_fan_speeds() is None


def test_sensors_are_none_without_hardware():
    assert sensors.get_cpu_temperature() is None
    assert sensors.get_fan_speeds() is None
