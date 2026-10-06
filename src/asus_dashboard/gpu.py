from asus_dashboard.status import run_command, read_sysfs, NVIDIA_GPU
from asus_dashboard.dbus_helpers import get_property

SWITCHEROO = "net.hadess.SwitcherooControl"
SWITCHEROO_PATH = "/net/hadess/SwitcherooControl"

MODE_NAMES = {
    "on-demand": "hybrid",
    "intel": "integrated",
    "nvidia": "nvidia",
}

PRIME_NAMES = {
    "hybrid": "on-demand",
    "integrated": "intel",
    "nvidia": "nvidia",
}

def get_gpu_mode() -> str | None:
    """Return the GPU mode as 'hybrid', 'integrated' or 'nvidia', or None if unknown"""
    output = run_command(["prime-select", "query"])
    if output is None:
        return None
    return MODE_NAMES.get(output, "unknown")

def get_gpu_names() -> list[str]:
    """Return the names of the GPUs in this laptop, or an empty list"""
    gpus = get_property(SWITCHEROO, SWITCHEROO_PATH, SWITCHEROO, "GPUs")
    if gpus is None:
        return []
    return [str(gpu["Name"]) for gpu in gpus]

def is_nvidia_awake() -> bool | None:
    """Return True if the Nvidia GPU is powered up, False if asleep, None if unknown"""
    status = read_sysfs(NVIDIA_GPU)
    if status is None:
        return None
    return status != "suspended"

def set_gpu_mode(mode: str) -> bool:
    """Switch the GPU mode (asks for the password). The change applies after a reboot."""
    if mode not in PRIME_NAMES:
        print(f"'{mode}' is not a valid GPU mode. Choices: {', '.join(PRIME_NAMES)}")
        return False

    output = run_command(["pkexec", "prime-select", PRIME_NAMES[mode]], 120)
    if output is None:
        return False

    print(f"GPU mode set to {mode}. Reboot to apply.")
    return True

if __name__ == "__main__":
    print("GPU mode:", get_gpu_mode())
    print("GPUs:", get_gpu_names())
    print("Nvidia awake?", is_nvidia_awake())
    print("Set turbo:", set_gpu_mode("turbo"))
    print("Set hybrid:", set_gpu_mode("hybrid"))
