import sys
from pathlib import Path

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from PySide6.QtCore import Qt, QSignalBlocker, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSlider, QStyle, QStyleOption, QVBoxLayout, QWidget,
)

from dbus_helpers import PROPERTIES
from performance import get_profile, get_profile_choices, set_profile
from performance import BUS_NAME as PROFILES, OBJECT_PATH as PROFILES_PATH
from gpu import get_gpu_mode, set_gpu_mode, PRIME_NAMES
from display import get_current_refresh_rate, get_refresh_rates, set_refresh_rate
from nightlight import get_night_light, set_night_light
from battery_info import get_battery_percentage, get_battery_state, UPOWER, BATTERY_PATH
from keyboard import get_keyboard_brightness, set_keyboard_brightness
from battery import get_charge_limit_value, set_charge_limit
from settings import get_setting, save_setting
from themes import THEMES, DEFAULT_THEME
from worker import Worker


REFRESH_INTERVAL_MS = 2000
PROJECT_DIR = Path(__file__).parent


def get_theme_name() -> str:
    """Return the saved theme name, or the default if nothing valid is saved"""
    name = get_setting("theme", DEFAULT_THEME)
    if name not in THEMES:
        return DEFAULT_THEME
    return name


def build_style(theme_name: str) -> str:
    """Return style.qss with the colours of one theme filled in, or '' (default look) if the file is missing"""
    try:
        style = (PROJECT_DIR / "style.qss").read_text()
    except FileNotFoundError:
        print("style.qss not found, using the default look")
        return ""
    style = style.replace("@ASSETS@", (PROJECT_DIR / "assets").as_posix())
    for name, colour in THEMES[theme_name].items():
        style = style.replace(f"@{name}@", colour)
    return style


def show(value, suffix: str = "") -> str:
    """Return the value as text with the suffix added, or 'not supported' if it is None"""
    if value is None:
        return "not supported"
    return f"{value}{suffix}"


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ASUS Dashboard")
        self.resize(780, 470)
        self.setObjectName("window")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        title = QLabel("ASUS TUF Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")

        self.gpu_worker = None

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        close_button = QPushButton("Close")

        theme_label = QLabel("Theme:")
        theme_label.setObjectName("themeLabel")
        self.theme_box = QComboBox()
        self.theme_box.setObjectName("themeBox")
        self.theme_box.addItems(list(THEMES))
        self.theme_box.setCurrentText(get_theme_name())

        grid = QGridLayout()
        grid.addWidget(self.build_performance_group(), 0, 0)
        grid.addWidget(self.build_display_group(), 0, 1)
        grid.addWidget(self.build_keyboard_group(), 1, 0)
        grid.addWidget(self.build_battery_group(), 1, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.status_label)
        bottom_row.addStretch()
        bottom_row.addWidget(theme_label)
        bottom_row.addWidget(self.theme_box)
        bottom_row.addWidget(close_button)
        layout.addLayout(bottom_row)
        self.setLayout(layout)

        close_button.clicked.connect(self.close)
        self.theme_box.currentTextChanged.connect(self.on_theme_changed)

        self.start_sync()

    def closeEvent(self, event) -> None:
        """Qt calls this when the window is asked to close. Refuse while the GPU job is still running"""
        if self.gpu_worker is not None and self.gpu_worker.isRunning():
            self.show_result(False, "Finish or cancel the password window before closing")
            event.ignore()
            return
        event.accept()

    def paintEvent(self, event) -> None:
        """Draw the window background from style.qss. Qt skips this by itself for a see-through window"""
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

    def build_performance_group(self) -> QGroupBox:
        """Build the Performance section: profile dropdown, GPU mode dropdown and its Apply button"""
        self.profile_box = QComboBox()
        profile = get_profile()
        choices = get_profile_choices()
        if profile is None or not choices:
            self.profile_box.setEnabled(False)
        else:
            self.profile_box.addItems(choices)
            self.profile_box.setCurrentText(profile)

        self.gpu_box = QComboBox()
        self.gpu_box.addItems(list(PRIME_NAMES))
        self.gpu_button = QPushButton("Apply (needs reboot)")
        gpu_mode = get_gpu_mode()
        if gpu_mode is None:
            self.gpu_box.setEnabled(False)
            self.gpu_button.setEnabled(False)
        else:
            self.gpu_box.setCurrentText(gpu_mode)

        form = QFormLayout()
        form.addRow("Profile:", self.profile_box)
        form.addRow("GPU mode:", self.gpu_box)
        form.addRow("", self.gpu_button)

        group = QGroupBox("Performance")
        group.setObjectName("performance")
        group.setLayout(form)

        self.profile_box.currentTextChanged.connect(self.on_profile_changed)
        self.gpu_button.clicked.connect(self.on_gpu_apply_clicked)
        return group

    def build_display_group(self) -> QGroupBox:
        """Build the Display section: refresh rate dropdown and night light tick box"""
        self.refresh_box = QComboBox()
        rates = get_refresh_rates()
        current_rate = get_current_refresh_rate()
        if current_rate is None or not rates:
            self.refresh_box.setEnabled(False)
        else:
            self.refresh_box.addItems([f"{rate} Hz" for rate in rates])
            self.refresh_box.setCurrentText(f"{current_rate} Hz")

        self.night_light_box = QCheckBox("Night light")
        night_light = get_night_light()
        if night_light is None:
            self.night_light_box.setEnabled(False)
        else:
            self.night_light_box.setChecked(night_light)

        form = QFormLayout()
        form.addRow("Refresh rate:", self.refresh_box)
        form.addRow("", self.night_light_box)

        group = QGroupBox("Display")
        group.setObjectName("display")
        group.setLayout(form)

        self.refresh_box.currentTextChanged.connect(self.on_refresh_rate_changed)
        self.night_light_box.toggled.connect(self.on_night_light_toggled)
        return group

    def build_keyboard_group(self) -> QGroupBox:
        """Build the Keyboard section: brightness slider with its number"""
        self.keyboard_slider = QSlider(Qt.Orientation.Horizontal)
        self.keyboard_slider.setRange(0, 3)
        self.keyboard_value = QLabel()
        brightness = get_keyboard_brightness()
        if brightness is None:
            self.keyboard_slider.setEnabled(False)
            self.keyboard_value.setText("not supported")
        else:
            self.keyboard_slider.setValue(brightness)
            self.keyboard_value.setText(str(brightness))

        keyboard_row = QHBoxLayout()
        keyboard_row.addWidget(self.keyboard_slider)
        keyboard_row.addWidget(self.keyboard_value)

        form = QFormLayout()
        form.addRow("Brightness:", keyboard_row)

        group = QGroupBox("Keyboard")
        group.setObjectName("keyboard")
        group.setLayout(form)

        self.keyboard_slider.valueChanged.connect(self.on_keyboard_changed)
        return group

    def build_battery_group(self) -> QGroupBox:
        """Build the Battery section: level label and charge limit slider with its number"""
        self.battery_label = QLabel(self.battery_text())

        self.charge_slider = QSlider(Qt.Orientation.Horizontal)
        self.charge_slider.setRange(20, 100)
        self.charge_value = QLabel()
        limit = get_charge_limit_value()
        if limit is None:
            self.charge_slider.setEnabled(False)
            self.charge_value.setText("not supported")
        else:
            self.charge_slider.setValue(limit)
            self.charge_value.setText(f"{limit}%")

        charge_row = QHBoxLayout()
        charge_row.addWidget(self.charge_slider)
        charge_row.addWidget(self.charge_value)

        form = QFormLayout()
        form.addRow("Level:", self.battery_label)
        form.addRow("Charge limit:", charge_row)

        group = QGroupBox("Battery")
        group.setObjectName("battery")
        group.setLayout(form)

        self.charge_slider.valueChanged.connect(self.on_charge_dragged)
        self.charge_slider.sliderReleased.connect(self.on_charge_released)
        return group

    def battery_text(self) -> str:
        """Return the battery level and state as one line of text, e.g. '80% (discharging)'"""
        percentage = get_battery_percentage()
        state = get_battery_state()
        text = show(percentage, "%")
        if percentage is not None and state is not None:
            text += f" ({state})"
        return text

    def start_sync(self) -> None:
        """Start following the system: D-Bus signals for what announces changes, a timer for the rest"""
        bus = dbus.SystemBus()
        bus.add_signal_receiver(
            self.on_profile_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface=PROPERTIES,
            bus_name=PROFILES,
            path=PROFILES_PATH,
        )
        bus.add_signal_receiver(
            self.on_battery_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface=PROPERTIES,
            bus_name=UPOWER,
            path=BATTERY_PATH,
        )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_from_system)
        self.timer.start(REFRESH_INTERVAL_MS)

    def on_profile_properties_changed(self, interface, changed, invalidated) -> None:
        """The system says the profile changed: show it without applying it again"""
        if "ActiveProfile" not in changed:
            return
        blocker = QSignalBlocker(self.profile_box)
        self.profile_box.setCurrentText(str(changed["ActiveProfile"]))
        del blocker

    def on_battery_properties_changed(self, interface, changed, invalidated) -> None:
        """The system says the battery level or state changed: refresh the level text"""
        if "Percentage" in changed or "State" in changed:
            self.battery_label.setText(self.battery_text())

    def refresh_from_system(self) -> None:
        """Runs on the timer: re-read what has no change signal and update the widgets quietly"""
        brightness = get_keyboard_brightness()
        if brightness is not None and brightness != self.keyboard_slider.value():
            blocker = QSignalBlocker(self.keyboard_slider)
            self.keyboard_slider.setValue(brightness)
            del blocker
            self.keyboard_value.setText(str(brightness))

        limit = get_charge_limit_value()
        if limit is not None and not self.charge_slider.isSliderDown() and limit != self.charge_slider.value():
            blocker = QSignalBlocker(self.charge_slider)
            self.charge_slider.setValue(limit)
            del blocker
            self.charge_value.setText(f"{limit}%")

        rate = get_current_refresh_rate()
        if rate is not None and f"{rate} Hz" != self.refresh_box.currentText():
            blocker = QSignalBlocker(self.refresh_box)
            self.refresh_box.setCurrentText(f"{rate} Hz")
            del blocker

        night_light = get_night_light()
        if night_light is not None and night_light != self.night_light_box.isChecked():
            blocker = QSignalBlocker(self.night_light_box)
            self.night_light_box.setChecked(night_light)
            del blocker

    def show_result(self, ok: bool, message: str) -> None:
        """Show the outcome of the last action in the status line"""
        self.status_label.setText(f"{'✓' if ok else '✗'} {message}")

    def on_theme_changed(self, name: str) -> None:
        """Re-colour the whole app with the chosen theme and remember the choice"""
        QApplication.instance().setStyleSheet(build_style(name))
        save_setting("theme", name)
        self.show_result(True, f"Theme changed to {name}")

    def on_profile_changed(self, text: str) -> None:
        ok = set_profile(text)
        self.show_result(ok, f"Profile set to {text}" if ok else f"Could not set profile to {text}")

    def on_gpu_apply_clicked(self) -> None:
        """Runs when Apply is clicked. Starts the slow job in a background thread and returns at once"""
        mode = self.gpu_box.currentText()
        self.gpu_box.setEnabled(False)
        self.gpu_button.setEnabled(False)
        self.status_label.setText("Waiting for password...")

        self.gpu_worker = Worker(set_gpu_mode, mode)
        self.gpu_worker.done.connect(self.on_gpu_apply_done)
        self.gpu_worker.start()

    def on_gpu_apply_done(self, ok: bool) -> None:
        """Runs in the main thread when the GPU job has finished"""
        mode = self.gpu_box.currentText()
        self.gpu_box.setEnabled(True)
        self.gpu_button.setEnabled(True)
        self.show_result(ok, f"GPU mode set to {mode}. Reboot to apply" if ok else f"Could not set GPU mode to {mode}")

    def on_refresh_rate_changed(self, text: str) -> None:
        rate = int(text.split()[0])
        ok = set_refresh_rate(rate)
        self.show_result(ok, f"Refresh rate set to {rate} Hz" if ok else f"Could not set refresh rate to {rate} Hz")

    def on_night_light_toggled(self, checked: bool) -> None:
        ok = set_night_light(checked)
        state = "on" if checked else "off"
        self.show_result(ok, f"Night light turned {state}" if ok else f"Could not turn night light {state}")

    def on_keyboard_changed(self, value: int) -> None:
        self.keyboard_value.setText(str(value))
        ok = set_keyboard_brightness(value)
        self.show_result(ok, f"Keyboard set to {value}" if ok else "Could not set keyboard brightness")

    def on_charge_dragged(self, value: int) -> None:
        """Only updates the number while dragging; nothing is applied yet"""
        self.charge_value.setText(f"{value}%")

    def on_charge_released(self) -> None:
        value = self.charge_slider.value()
        ok = set_charge_limit(value)
        self.show_result(ok, f"Charge limit set to {value}%" if ok else "Could not set charge limit")


if __name__ == "__main__":
    DBusGMainLoop(set_as_default=True)
    app = QApplication(sys.argv)
    app.setStyleSheet(build_style(get_theme_name()))
    window = Dashboard()
    window.show()
    sys.exit(app.exec())
