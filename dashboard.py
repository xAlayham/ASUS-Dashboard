import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)

from performance import get_profile, get_profile_choices, set_profile
from gpu import get_gpu_mode
from display import get_current_refresh_rate
from battery_info import get_battery_percentage, get_battery_state
from keyboard import get_keyboard_brightness, set_keyboard_brightness
from battery import get_charge_limit_value, set_charge_limit


def show(value, suffix: str = "") -> str:
    """Return the value as text with the suffix added, or 'not supported' if it is None"""
    if value is None:
        return "not supported"
    return f"{value}{suffix}"


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ASUS Dashboard")
        self.resize(420, 300)

        title = QLabel("ASUS TUF Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        percentage = get_battery_percentage()
        state = get_battery_state()
        battery = show(percentage, "%")
        if percentage is not None and state is not None:
            battery += f" ({state})"

        self.profile_box = QComboBox()
        profile = get_profile()
        choices = get_profile_choices()
        if profile is None or not choices:
            self.profile_box.setEnabled(False)
        else:
            self.profile_box.addItems(choices)
            self.profile_box.setCurrentText(profile)

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

        self.status_label = QLabel("")
        close_button = QPushButton("Close")

        keyboard_row = QHBoxLayout()
        keyboard_row.addWidget(self.keyboard_slider)
        keyboard_row.addWidget(self.keyboard_value)

        charge_row = QHBoxLayout()
        charge_row.addWidget(self.charge_slider)
        charge_row.addWidget(self.charge_value)

        form = QFormLayout()
        form.addRow("Performance profile:", self.profile_box)
        form.addRow("GPU mode:", QLabel(show(get_gpu_mode())))
        form.addRow("Refresh rate:", QLabel(show(get_current_refresh_rate(), " Hz")))
        form.addRow("Battery:", QLabel(battery))
        form.addRow("Charge limit:", charge_row)
        form.addRow("Keyboard backlight:", keyboard_row)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(close_button)
        self.setLayout(layout)

        self.profile_box.currentTextChanged.connect(self.on_profile_changed)
        self.keyboard_slider.valueChanged.connect(self.on_keyboard_changed)
        self.charge_slider.valueChanged.connect(self.on_charge_dragged)
        self.charge_slider.sliderReleased.connect(self.on_charge_released)
        close_button.clicked.connect(self.close)

    def show_result(self, ok: bool, message: str) -> None:
        """Show the outcome of the last action in the status line"""
        self.status_label.setText(f"{'✓' if ok else '✗'} {message}")

    def on_profile_changed(self, text: str) -> None:
        ok = set_profile(text)
        self.show_result(ok, f"Profile set to {text}" if ok else f"Could not set profile to {text}")

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
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())