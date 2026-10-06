import pytest

import gpu


@pytest.fixture
def nvidia_status(tmp_path, monkeypatch):
    """A pretend runtime_status file for the Nvidia card"""
    path = tmp_path / "runtime_status"
    monkeypatch.setattr(gpu, "NVIDIA_GPU", path)
    return path


@pytest.mark.parametrize("status, expected", [
    ("suspended", False),
    ("active", True),
    ("resuming", True),
    ("suspending", True),
])
def test_is_nvidia_awake_reads_the_power_state(nvidia_status, status, expected):
    nvidia_status.write_text(status + "\n")
    assert gpu.is_nvidia_awake() is expected


def test_is_nvidia_awake_is_none_when_the_card_is_switched_off():
    assert gpu.is_nvidia_awake() is None


def test_every_gpu_mode_can_be_translated_both_ways():
    for name, prime_name in gpu.PRIME_NAMES.items():
        assert gpu.MODE_NAMES[prime_name] == name


def test_set_gpu_mode_refuses_an_unknown_mode_without_running_anything():
    assert gpu.set_gpu_mode("turbo") is False
