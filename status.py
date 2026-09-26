from pathlib import Path

PROFILE = Path("/sys/firmware/acpi")
ARMOURY = Path("/sys/class/firmware-attributes/asus-armoury/attributes")
NVIDIA_GPU = Path("/sys/bus/pci/devices/0000:01:00.0/power/runtime_status")
SCREEN = Path("/sys/class/backlight/intel_backlight")
KEYBOARD = Path("/sys/class/leds/asus::kbd_backlight")
BATTERY = Path("/sys/class/power_supply/BAT1")
HWMON = Path("/sys/class/hwmon")

NOT_SUPPORTED = "not supported"

def read_sysfs(path: Path) -> str | None:
    """Return the text inside a sysfile, returns None if it can't be read"""
    try:
        return path.read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None

def percent(value_path: Path, max_path: Path) -> str:
    """Read a value and its maximum and return it as a whole-number percentage"""
    value = read_sysfs(value_path)
    maximum = read_sysfs(max_path)
    if value is None or maximum is None or int(maximum) == 0:
        return NOT_SUPPORTED
    return f"{round(int(value) / int(maximum) * 100)}%"

def find_hwmon(name: str) -> Path | None:
    """Find the hwmon folder whose 'name' file matches the given name"""
    for folder in HWMON.glob("hwmon*"):
        if read_sysfs(folder / "name") == name:
            return folder
    return None

def get_profile() -> str:
    current = read_sysfs(PROFILE / "platform_profile")
    if current is None:
        return NOT_SUPPORTED
    choices = read_sysfs(PROFILE / "platform_profile_choices")
    if choices is None:
        return current
    return f"{current} (options: {', '.join(choices.split())})"

def get_gpu_mode() -> str:
    value = read_sysfs(ARMOURY / "dgpu_disable" / "current_value")
    if value is None:
        return NOT_SUPPORTED
    return "Eco" if value == "1" else "Hybrid"

def get_nvidia_status() -> str:
    return read_sysfs(NVIDIA_GPU) or NOT_SUPPORTED

def get_overdrive() -> str:
    value = read_sysfs(ARMOURY / "panel_overdrive" / "current_value")
    if value is None:
        return NOT_SUPPORTED
    return "on" if value == "1" else "off"

def get_keyboard() -> str:
    value = read_sysfs(KEYBOARD / "brightness")
    maximum = read_sysfs(KEYBOARD / "max_brightness")
    if value is None or maximum is None:
        return NOT_SUPPORTED
    return f"{value}/{maximum}"
 
 
def get_battery() -> str:
    capacity = read_sysfs(BATTERY / "capacity")
    if capacity is None:
        return NOT_SUPPORTED
    status = read_sysfs(BATTERY / "status")
    return f"{capacity}% ({status})" if status else f"{capacity}%"
 
 
def get_charge_limit() -> str:
    limit = read_sysfs(BATTERY / "charge_control_end_threshold")
    return f"{limit}%" if limit else NOT_SUPPORTED
 
 
def get_fans() -> str:
    asus = find_hwmon("asus")
    if asus is None:
        return NOT_SUPPORTED
    cpu = read_sysfs(asus / "fan1_input")
    gpu = read_sysfs(asus / "fan2_input")
    if cpu is None or gpu is None:
        return NOT_SUPPORTED
    return f"CPU {cpu} RPM, GPU {gpu} RPM"
 
 
def get_cpu_temp() -> str:
    coretemp = find_hwmon("coretemp")
    if coretemp is None:
        return NOT_SUPPORTED
    value = read_sysfs(coretemp / "temp1_input")
    if value is None:
        return NOT_SUPPORTED
    return f"{int(value) / 1000:.1f} °C"
 
def main() -> None:
    rows = [
        ("Performance profile", get_profile()),
        ("GPU mode", get_gpu_mode()),
        ("Nvidia GPU", get_nvidia_status()),
        ("Screen brightness", percent(SCREEN / "brightness", SCREEN / "max_brightness")),
        ("Panel overdrive", get_overdrive()),
        ("Keyboard backlight", get_keyboard()),
        ("Battery", get_battery()),
        ("Charge limit", get_charge_limit()),
        ("Battery health", percent(BATTERY / "charge_full", BATTERY / "charge_full_design")),
        ("Fans", get_fans()),
        ("CPU temperature", get_cpu_temp()),
    ]

    print("=== ASUS TUF STATUS ===")
    for label, value in rows:
        print(f"{label:<19}: {value}")

if __name__ == "__main__":
    main()