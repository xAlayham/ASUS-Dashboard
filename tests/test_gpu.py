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


def test_set_gpu_mode_refuses_an_unknown_mode_without_running_anything(fake_command):
    assert gpu.set_gpu_mode("turbo") is False
    assert fake_command.calls == []


@pytest.mark.parametrize("output, expected", [
    ("on-demand", "hybrid"),
    ("intel", "integrated"),
    ("nvidia", "nvidia"),
    ("something-new", "unknown"),
])
def test_get_gpu_mode_translates_the_name(fake_command, output, expected):
    fake_command.output = output
    assert gpu.get_gpu_mode() == expected
    assert fake_command.calls == [["prime-select", "query"]]


def test_get_gpu_mode_is_none_without_prime_select(fake_command):
    fake_command.output = None
    assert gpu.get_gpu_mode() is None


@pytest.mark.parametrize("mode, prime_name", [
    ("hybrid", "on-demand"),
    ("integrated", "intel"),
    ("nvidia", "nvidia"),
])
def test_set_gpu_mode_asks_for_the_password_and_waits_long_enough(fake_command, mode, prime_name):
    assert gpu.set_gpu_mode(mode) is True
    assert fake_command.calls == [["pkexec", "prime-select", prime_name]]
    assert fake_command.timeouts == [120]


def test_set_gpu_mode_is_false_when_the_password_is_cancelled(fake_command):
    fake_command.output = None
    assert gpu.set_gpu_mode("hybrid") is False


def test_get_gpu_names_lists_each_gpu(fake_properties):
    fake_properties.values["GPUs"] = [
        {"Name": "NVIDIA GeForce RTX 2050", "Default": False},
        {"Name": "Intel UHD Graphics", "Default": True},
    ]
    assert gpu.get_gpu_names() == ["NVIDIA GeForce RTX 2050", "Intel UHD Graphics"]


def test_get_gpu_names_is_empty_without_the_service(fake_properties):
    assert gpu.get_gpu_names() == []
