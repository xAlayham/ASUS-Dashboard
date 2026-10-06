from pathlib import Path

from asus_dashboard.status import find_hwmon, read_sysfs, BATTERY

PROC_STAT = Path("/proc/stat")


def get_cpu_temperature() -> float | None:
    """Return the CPU package temperature in °C, or None if unsupported"""
    coretemp = find_hwmon("coretemp")
    if coretemp is None:
        return None
    value = read_sysfs(coretemp / "temp1_input")
    if value is None:
        return None
    return int(value) / 1000


def get_fan_speeds() -> tuple[int, int] | None:
    """Return the (CPU fan, GPU fan) speeds in RPM, or None if unsupported"""
    asus = find_hwmon("asus")
    if asus is None:
        return None
    cpu = read_sysfs(asus / "fan1_input")
    gpu = read_sysfs(asus / "fan2_input")
    if cpu is None or gpu is None:
        return None
    return int(cpu), int(gpu)


def get_power_draw() -> float | None:
    """Return the watts being drawn from the battery, or None when it is not discharging"""
    if read_sysfs(BATTERY / "status") != "Discharging":
        return None
    current = read_sysfs(BATTERY / "current_now")
    voltage = read_sysfs(BATTERY / "voltage_now")
    if current is None or voltage is None:
        return None
    return int(current) * int(voltage) / 1_000_000_000_000


def read_cpu_times() -> tuple[int, int] | None:
    """Return (total time, idle time) the CPU has spent since boot, or None if unreadable"""
    text = read_sysfs(PROC_STAT)
    if text is None:
        return None
    fields = [int(field) for field in text.splitlines()[0].split()[1:]]
    idle = fields[3] + fields[4]
    return sum(fields), idle


class CpuUsage:
    """Works out CPU usage by comparing each reading of /proc/stat with the one before it."""

    def __init__(self):
        self.previous = read_cpu_times()

    def read(self) -> float | None:
        """Return the percentage of time the CPU was busy since the last call, or None if unknown"""
        current = read_cpu_times()
        previous = self.previous
        self.previous = current
        if current is None or previous is None:
            return None

        total = current[0] - previous[0]
        idle = current[1] - previous[1]
        if total <= 0:
            return None
        return (total - idle) / total * 100


if __name__ == "__main__":
    import time

    usage = CpuUsage()
    time.sleep(1)
    print("CPU temperature:", get_cpu_temperature())
    print("Fan speeds:", get_fan_speeds())
    print("Power draw:", get_power_draw())
    print("CPU usage:", usage.read())
