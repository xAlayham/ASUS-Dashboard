from settings import save_setting
from status import run_command

OUTPUT = "eDP-1"

def get_current_mode_line() -> str | None:
    """Returns the xrandr line for current display mode, or None"""
    output = run_command(["xrandr", "--query"])
    if not output:
        return None
    for line in output.splitlines():
        if "*" in line:
            return line.strip()
    return None

def get_refresh_rates() -> list[int]:
    """Returns list of all available refresh rate settings"""
    line = get_current_mode_line()
    if line is None:
        return []

    rates = []
    for part in line.split()[1:]:
        cleaned = part.strip("*+")
        if not cleaned:
            continue
        rate = round(float(cleaned))
        if rate not in rates:
            rates.append(rate)
    return rates

def get_current_refresh_rate() -> int | None:
    """Returns current active refresh rate, or None"""
    line = get_current_mode_line()
    if line is None:
        return None

    for part in line.split():
        if "*" in part:
            return round(float(part.strip("*+")))
    return None

def set_refresh_rate(rate: int) -> bool:
    """Return True if refresh rate change was sucessful, else return False"""
    if rate not in get_refresh_rates():
        return False

    line = get_current_mode_line()
    if line is None:
        return False
    resolution = line.split()[0]

    output = run_command(["xrandr", "--output", OUTPUT, "--mode", resolution, "--rate", str(rate)])
    if output is None:
        return False

    save_setting("refresh_rate", rate)
    return True

if __name__ == "__main__":
    print("Available rates:", get_refresh_rates())
    print("Current rate:", get_current_refresh_rate())

    print("Set 60:", set_refresh_rate(60))
    print("Rate now:", get_current_refresh_rate())

    print("Set 75 (should fail):", set_refresh_rate(75))

    print("Set 144:", set_refresh_rate(144))
    print("Rate now:", get_current_refresh_rate())