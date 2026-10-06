import sys

import install_desktop
from install_desktop import ENTRY_NAME


def test_build_entry_for_the_launcher_starts_the_dashboard():
    text = install_desktop.build_entry(hidden=False)
    assert text.startswith("[Desktop Entry]\n")
    assert text.endswith("\n")
    assert "dashboard.py" in text
    assert "--hidden" not in text
    assert "X-GNOME-Autostart-enabled" not in text


def test_build_entry_for_autostart_starts_hidden():
    text = install_desktop.build_entry(hidden=True)
    assert 'dashboard.py" --hidden\n' in text
    assert "X-GNOME-Autostart-enabled=true" in text


def test_build_entry_uses_full_paths():
    for line in install_desktop.build_entry(hidden=False).splitlines():
        if line.startswith("Exec="):
            assert line.startswith('Exec="/')
        if line.startswith("Icon="):
            assert line.startswith("Icon=/")


def test_find_python_prefers_the_project_venv(tmp_path, monkeypatch):
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")
    monkeypatch.setattr(install_desktop, "PROJECT_DIR", tmp_path)
    assert install_desktop.find_python() == venv_python


def test_find_python_falls_back_to_the_running_python(tmp_path, monkeypatch):
    monkeypatch.setattr(install_desktop, "PROJECT_DIR", tmp_path)
    assert str(install_desktop.find_python()) == sys.executable


def test_autostart_is_off_in_an_empty_folder(tmp_path):
    assert install_desktop.is_autostart_enabled(tmp_path) is False


def test_set_autostart_on_writes_a_hidden_entry(tmp_path):
    folder = tmp_path / "autostart"
    assert install_desktop.set_autostart(True, folder) is True
    assert install_desktop.is_autostart_enabled(folder) is True
    assert "--hidden" in (folder / ENTRY_NAME).read_text()


def test_set_autostart_off_removes_the_entry(tmp_path):
    install_desktop.set_autostart(True, tmp_path)
    assert install_desktop.set_autostart(False, tmp_path) is True
    assert install_desktop.is_autostart_enabled(tmp_path) is False


def test_set_autostart_can_be_repeated(tmp_path):
    assert install_desktop.set_autostart(False, tmp_path) is True
    assert install_desktop.set_autostart(True, tmp_path) is True
    assert install_desktop.set_autostart(True, tmp_path) is True
    assert install_desktop.is_autostart_enabled(tmp_path) is True


def test_set_autostart_is_false_when_the_folder_cannot_be_made(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("")
    assert install_desktop.set_autostart(True, blocker / "autostart") is False


def test_install_writes_the_launcher_and_the_autostart_entry(tmp_path):
    applications = tmp_path / "applications"
    autostart = tmp_path / "autostart"
    written = install_desktop.install(applications, autostart)
    assert written == [applications / ENTRY_NAME, autostart / ENTRY_NAME]
    assert "--hidden" not in (applications / ENTRY_NAME).read_text()
    assert "--hidden" in (autostart / ENTRY_NAME).read_text()


def test_remove_deletes_both_entries(tmp_path):
    applications = tmp_path / "applications"
    autostart = tmp_path / "autostart"
    install_desktop.install(applications, autostart)
    assert install_desktop.remove(applications, autostart) == [applications / ENTRY_NAME, autostart / ENTRY_NAME]
    assert not (applications / ENTRY_NAME).exists()
    assert not (autostart / ENTRY_NAME).exists()


def test_remove_does_nothing_when_nothing_is_installed(tmp_path):
    assert install_desktop.remove(tmp_path, tmp_path) == []
