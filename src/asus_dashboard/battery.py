from asus_dashboard.status import read_sysfs, write_sysfs, BATTERY
from asus_dashboard.settings import save_setting, load_settings

def set_charge_limit(limit: int) -> bool:
    """Sets battery charging limit to 20-100, rejects anything past this limit"""
    if limit > 100 or limit < 20:
        print("Charge limit must be between 20 and 100")
        return False

    ok = write_sysfs(BATTERY / "charge_control_end_threshold", str(limit))
    if ok:
        save_setting("charge_limit", limit)
        print(f"Charge limit is now: {limit}")
    return ok

def get_charge_limit_value() -> int | None:
    """Return the charge limit as a number (e.g. 80), or None if unsupported"""
    value = read_sysfs(BATTERY / "charge_control_end_threshold")
    if value is None:
        return None
    return int(value)

if __name__ == "__main__":
    print(set_charge_limit(70))
    print(f"Charge limit read back: {read_sysfs(BATTERY / 'charge_control_end_threshold')}")
    print(set_charge_limit(10))
    print(set_charge_limit(101))
    print(set_charge_limit(80))
    print(load_settings())
