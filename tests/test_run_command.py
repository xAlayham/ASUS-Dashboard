import subprocess
from types import SimpleNamespace

from asus_dashboard import status


def finished(returncode: int, stdout: str = "", stderr: str = ""):
    """Build a stand-in for what subprocess.run returns"""
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_command_returns_the_output_without_the_newline(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: finished(0, "on-demand\n"))
    assert status.run_command(["prime-select", "query"]) == "on-demand"


def test_run_command_returns_an_empty_string_when_a_command_prints_nothing(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: finished(0))
    assert status.run_command(["gsettings", "set"]) == ""


def test_run_command_is_none_and_shows_the_error_when_the_program_fails(monkeypatch, capsys):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: finished(1, stderr="no such key\n"))
    assert status.run_command(["gsettings", "get", "x"]) is None
    output = capsys.readouterr().out
    assert "gsettings get x" in output
    assert "no such key" in output


def test_run_command_is_none_when_the_program_is_not_installed(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    assert status.run_command(["no-such-program"]) is None


def test_run_command_is_none_when_the_program_takes_too_long(monkeypatch):
    def too_slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="slow", timeout=5)

    monkeypatch.setattr(subprocess, "run", too_slow)
    assert status.run_command(["slow"]) is None


def test_run_command_passes_the_command_and_timeout_on(monkeypatch):
    seen = []

    def record(args, **kwargs):
        seen.append((args, kwargs["timeout"]))
        return finished(0)

    monkeypatch.setattr(subprocess, "run", record)
    status.run_command(["one"])
    status.run_command(["two"], 120)
    assert seen == [(["one"], 5), (["two"], 120)]
