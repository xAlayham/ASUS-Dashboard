import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from performance import get_profile
from gpu import get_gpu_mode
from display import get_current_refresh_rate
from battery_info import get_battery_percentage, get_battery_state
from status import get_charge_limit, get_keyboard


def show(value, suffix: str = "") -> str:
    """Return the value as text with the suffix added, or 'not supported' if it is None"""
    if value is None:
        return "not supported"
    return f"{value}{suffix}"


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Window setup
        self.setWindowTitle("ASUS Dashboard")
        self.resize(420, 300)

        # 2. Widgets
        title = QLabel("ASUS TUF Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close_button = QPushButton("Close")

        percentage = get_battery_percentage()
        state = get_battery_state()
        battery = show(percentage, "%")
        if percentage is not None and state is not None:
            battery += f" ({state})"

        # 3. Layout
        form = QFormLayout()
        form.addRow("Performance profile:", QLabel(show(get_profile())))
        form.addRow("GPU mode:", QLabel(show(get_gpu_mode())))
        form.addRow("Refresh rate:", QLabel(show(get_current_refresh_rate(), " Hz")))
        form.addRow("Battery:", QLabel(battery))
        form.addRow("Charge limit:", QLabel(get_charge_limit()))
        form.addRow("Keyboard backlight:", QLabel(get_keyboard()))

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(close_button)
        self.setLayout(layout)

        # 4. Connections
        close_button.clicked.connect(self.close)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())