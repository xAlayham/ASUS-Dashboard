import os
import signal
import sys
from functools import partial
from pathlib import Path

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from PySide6.QtCore import Qt, QSignalBlocker, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy, QSlider, QStyle, QStyleOption,
    QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
)

from asus_dashboard.dbus_helpers import PROPERTIES
from asus_dashboard.performance import get_profile, get_profile_choices, set_profile
from asus_dashboard.performance import BUS_NAME as PROFILES, OBJECT_PATH as PROFILES_PATH
from asus_dashboard.gpu import get_gpu_mode, set_gpu_mode, is_nvidia_awake, PRIME_NAMES
from asus_dashboard.display import get_current_refresh_rate, get_refresh_rates, set_refresh_rate
from asus_dashboard.display import get_screen_brightness, set_screen_brightness, MIN_SCREEN_BRIGHTNESS
from asus_dashboard.nightlight import get_night_light, set_night_light
from asus_dashboard.battery_info import get_battery_percentage, get_battery_state, is_on_battery, UPOWER, UPOWER_PATH, BATTERY_PATH
from asus_dashboard.keyboard import get_keyboard_brightness, set_keyboard_brightness
from asus_dashboard.keyboard import get_keyboard_rgb, set_keyboard_rgb, RGB_EFFECTS, RGB_SPEEDS, EFFECTS_WITH_COLOUR, EFFECTS_WITH_SPEED
from asus_dashboard.battery import get_charge_limit_value, set_charge_limit
from asus_dashboard.settings import get_setting, save_setting
from asus_dashboard.themes import THEMES, DEFAULT_THEME
from asus_dashboard.worker import Worker
from asus_dashboard.sensors import get_cpu_temperature, get_fan_speeds, get_power_draw, CpuUsage
from asus_dashboard.sparkline import Sparkline
from asus_dashboard.presets import PRESETS, apply_preset, describe_preset, find_matching_preset
from asus_dashboard.automation import choose_preset, DEFAULT_CHARGER_PRESET, DEFAULT_BATTERY_PRESET
from asus_dashboard.install_desktop import is_autostart_enabled, set_autostart


REFRESH_INTERVAL_MS = 2000
SENSOR_INTERVAL_MS = 1000
PACKAGE_DIR = Path(__file__).parent
APP_NAME = "ASUS Dashboard"
SERVER_NAME = f"asus-dashboard-{os.getuid()}"
ICON_PATH = PACKAGE_DIR / "assets" / "icon.svg"
WINDOW_WIDTH_SHARE = 0.42
WINDOW_HEIGHT_SHARE = 0.52
NO_COPY = "none"
COPY_SHOWN = "shown"
COPY_STUCK = "stuck"
CUSTOM = "Custom"
CUSTOM_HINT = "your own mix of settings"


def ask_running_copy_to_show() -> str:
    """Ask a dashboard that is already running to show its window, and say what happened.

    Returns NO_COPY if none is running, COPY_SHOWN if one answered, or COPY_STUCK if one exists
    but did not answer. A copy that is suspended or frozen still accepts the connection, so only
    its reply proves that it is alive.
    """
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(500):
        return NO_COPY
    if socket.waitForReadyRead(1500):
        return COPY_SHOWN
    return COPY_STUCK


def wrap_in_scroll_area(content: QWidget) -> QScrollArea:
    """Put a widget in a scroll area, so the window can be smaller than the widget needs"""
    content.setObjectName("tabContent")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QScrollArea.Shape.NoFrame)
    area.viewport().setAutoFillBackground(False)
    area.setWidget(content)
    return area


def get_theme_name() -> str:
    """Return the saved theme name, or the default if nothing valid is saved"""
    name = get_setting("theme", DEFAULT_THEME)
    if name not in THEMES:
        return DEFAULT_THEME
    return name


def get_saved_preset(key: str, default: str) -> str:
    """Return the preset name saved under a settings key, or the default if nothing valid is saved"""
    name = get_setting(key, default)
    if name not in PRESETS:
        return default
    return name


def build_style(theme_name: str) -> str:
    """Return style.qss with the colours of one theme filled in, or '' (default look) if the file is missing"""
    try:
        style = (PACKAGE_DIR / "style.qss").read_text()
    except FileNotFoundError:
        print("style.qss not found, using the default look")
        return ""
    style = style.replace("@ASSETS@", (PACKAGE_DIR / "assets").as_posix())
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

        self.setWindowTitle(APP_NAME)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * WINDOW_WIDTH_SHARE), int(screen.height() * WINDOW_HEIGHT_SHARE))
        self.setMinimumSize(360, 280)
        self.setObjectName("window")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        title = QLabel("ASUS TUF Dashboard")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")

        self.gpu_worker = None
        self.on_battery = is_on_battery()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        close_button = QPushButton("Close")

        theme_label = QLabel("Theme:")
        theme_label.setObjectName("themeLabel")
        self.theme_box = QComboBox()
        self.theme_box.setObjectName("themeBox")
        self.theme_box.addItems(list(THEMES))
        self.theme_box.setCurrentText(get_theme_name())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.build_controls_tab(), "Controls")
        self.tabs.addTab(self.build_monitor_tab(), "Monitor")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addLayout(self.build_preset_row())
        layout.addWidget(self.tabs, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.status_label, 1)
        bottom_row.addWidget(theme_label)
        bottom_row.addWidget(self.theme_box)
        bottom_row.addWidget(close_button)
        layout.addLayout(bottom_row)
        self.setLayout(layout)

        close_button.clicked.connect(self.close)
        self.theme_box.currentTextChanged.connect(self.on_theme_changed)

        self.build_tray()
        self.start_single_instance_server()
        self.start_sync()

    def build_controls_tab(self) -> QScrollArea:
        """Build the Controls tab: every setting you can change, in a scrollable grid of sections"""
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 6, 0)
        grid.addWidget(self.build_automation_group(), 0, 0, 1, 2)
        grid.addWidget(self.build_performance_group(), 1, 0)
        grid.addWidget(self.build_display_group(), 1, 1)
        grid.addWidget(self.build_keyboard_group(), 2, 0)
        grid.addWidget(self.build_battery_group(), 2, 1)
        grid.setRowStretch(3, 1)

        content = QWidget()
        content.setLayout(grid)
        return wrap_in_scroll_area(content)

    def build_monitor_tab(self) -> QScrollArea:
        """Build the Monitor tab: the live readings and their graphs"""
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 6, 0)
        box.addWidget(self.build_live_group())

        content = QWidget()
        content.setLayout(box)
        return wrap_in_scroll_area(content)

    def build_tray(self) -> None:
        """Create the tray icon and its menu: show the window, switch profile, or quit"""
        show_action = QAction("Show dashboard", self)
        quit_action = QAction("Quit", self)

        self.tray_menu = QMenu()
        self.tray_menu.addAction(show_action)
        profile_menu = self.tray_menu.addMenu("Profile")
        for name in PRESETS:
            action = QAction(name, self)
            action.triggered.connect(partial(self.on_tray_preset_chosen, name))
            profile_menu.addAction(action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        self.tray = QSystemTrayIcon(QIcon(str(ICON_PATH)), self)
        self.tray.setToolTip(APP_NAME)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()
        self.tray_hint_shown = False

        show_action.triggered.connect(self.show_window)
        quit_action.triggered.connect(self.on_quit_requested)

    def start_single_instance_server(self) -> None:
        """Listen for other copies being started, and show this window when one is"""
        QLocalServer.removeServer(SERVER_NAME)
        self.server = QLocalServer(self)
        self.server.listen(SERVER_NAME)
        self.server.newConnection.connect(self.on_other_copy_started)

    def on_other_copy_started(self) -> None:
        """Runs when another copy is launched: answer it, so it knows this one is alive, and show the window"""
        connection = self.server.nextPendingConnection()
        if connection is not None:
            connection.write(b"shown")
            connection.flush()
            connection.disconnected.connect(connection.deleteLater)
        self.show_window()

    def show_window(self) -> None:
        """Bring the window back from the tray and put it in front"""
        self.show()
        self.raise_()
        self.activateWindow()

    def gpu_job_running(self) -> bool:
        """Return True while the GPU mode change is still waiting or working in the background"""
        return self.gpu_worker is not None and self.gpu_worker.isRunning()

    def notify(self, message: str) -> None:
        """Show a desktop notification, but only while the window is hidden and its status line can't be seen"""
        if not self.isVisible():
            self.tray.showMessage(APP_NAME, message, QIcon(str(ICON_PATH)))

    def on_tray_preset_chosen(self, name: str) -> None:
        """Runs when a profile is picked from the tray menu"""
        self.on_preset_chosen(name)
        self.notify(self.status_label.text())

    def on_quit_requested(self) -> None:
        """Runs when Quit is picked from the tray menu. Refuse while the GPU job is still running"""
        if self.gpu_job_running():
            self.show_window()
            self.show_result(False, "Finish or cancel the password window before quitting")
            return
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:
        """Closing the window only hides it to the tray. Quit in the tray menu ends the app"""
        event.ignore()
        if self.gpu_job_running():
            self.show_result(False, "Finish or cancel the password window before closing")
            return
        self.hide()
        if not self.tray_hint_shown:
            self.tray_hint_shown = True
            self.tray.showMessage(APP_NAME, "Still running in the tray. Use its menu to quit.", QIcon(str(ICON_PATH)))

    def showEvent(self, event) -> None:
        """Qt calls this when the window becomes visible: catch up, then keep the controls and readings updating"""
        super().showEvent(event)
        self.refresh_from_system()
        self.refresh_sensors()
        self.timer.start(REFRESH_INTERVAL_MS)
        self.sensor_timer.start(SENSOR_INTERVAL_MS)

    def hideEvent(self, event) -> None:
        """Qt calls this when the window is hidden: stop the timers, since nobody can see the results"""
        super().hideEvent(event)
        self.timer.stop()
        self.sensor_timer.stop()

    def paintEvent(self, event) -> None:
        """Draw the window background from style.qss. Qt skips this by itself for a see-through window"""
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

    def build_preset_row(self) -> QHBoxLayout:
        """Build the Profile row: a dropdown of presets and a line saying what the chosen one sets"""
        preset_label = QLabel("Profile:")
        preset_label.setObjectName("presetLabel")

        self.preset_box = QComboBox()
        self.preset_box.setObjectName("presetBox")
        self.preset_box.addItem(CUSTOM)
        self.preset_box.setItemData(0, CUSTOM_HINT, Qt.ItemDataRole.ToolTipRole)
        for name in PRESETS:
            self.preset_box.addItem(name)
            self.preset_box.setItemData(self.preset_box.count() - 1, describe_preset(name), Qt.ItemDataRole.ToolTipRole)

        self.preset_hint = QLabel()
        self.preset_hint.setObjectName("presetHint")
        self.preset_hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.show_preset(find_matching_preset(self.current_state()))

        row = QHBoxLayout()
        row.addWidget(preset_label)
        row.addWidget(self.preset_box)
        row.addWidget(self.preset_hint, 1)

        self.preset_box.currentTextChanged.connect(self.on_preset_chosen)
        return row

    def build_automation_group(self) -> QGroupBox:
        """Build the Automation section: automatic profile switching, and starting at login"""
        self.auto_box = QCheckBox("Switch automatically")
        self.auto_box.setObjectName("autoCheck")
        enabled = bool(get_setting("auto_switch", False))
        self.auto_box.setChecked(enabled)

        charger_label = QLabel("On charger:")
        charger_label.setObjectName("autoLabel")
        self.charger_box = QComboBox()
        self.charger_box.setObjectName("autoBox")
        self.charger_box.addItems(list(PRESETS))
        self.charger_box.setCurrentText(get_saved_preset("charger_preset", DEFAULT_CHARGER_PRESET))
        self.charger_box.setEnabled(enabled)

        battery_label = QLabel("On battery:")
        battery_label.setObjectName("autoLabel")
        self.battery_box = QComboBox()
        self.battery_box.setObjectName("autoBox")
        self.battery_box.addItems(list(PRESETS))
        self.battery_box.setCurrentText(get_saved_preset("battery_preset", DEFAULT_BATTERY_PRESET))
        self.battery_box.setEnabled(enabled)

        row = QHBoxLayout()
        row.addWidget(self.auto_box)
        row.addSpacing(12)
        row.addWidget(charger_label)
        row.addWidget(self.charger_box)
        row.addSpacing(12)
        row.addWidget(battery_label)
        row.addWidget(self.battery_box)
        row.addStretch()

        self.autostart_box = QCheckBox("Start at login, hidden in the tray")
        self.autostart_box.setObjectName("autoCheck")
        self.autostart_box.setChecked(is_autostart_enabled())

        box = QVBoxLayout()
        box.addLayout(row)
        box.addWidget(self.autostart_box)

        group = QGroupBox("Automation")
        group.setObjectName("automation")
        group.setLayout(box)

        self.auto_box.toggled.connect(self.charger_box.setEnabled)
        self.auto_box.toggled.connect(self.battery_box.setEnabled)
        self.autostart_box.toggled.connect(self.on_autostart_toggled)
        self.auto_box.toggled.connect(partial(save_setting, "auto_switch"))
        self.charger_box.currentTextChanged.connect(partial(save_setting, "charger_preset"))
        self.battery_box.currentTextChanged.connect(partial(save_setting, "battery_preset"))
        return group

    def current_state(self) -> dict:
        """Return the current value of every setting a preset can change"""
        return {
            "profile": get_profile(),
            "refresh_rate": get_current_refresh_rate(),
            "keyboard_brightness": get_keyboard_brightness(),
        }

    def show_preset(self, name: str | None) -> None:
        """Make the Profile dropdown and its hint show the given preset, or Custom for None, without applying it"""
        text = CUSTOM if name is None else name
        if text != self.preset_box.currentText():
            blocker = QSignalBlocker(self.preset_box)
            self.preset_box.setCurrentText(text)
            del blocker
        self.preset_hint.setText(CUSTOM_HINT if name is None else describe_preset(name))

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
        form.addRow("Power mode:", self.profile_box)
        form.addRow("GPU mode:", self.gpu_box)
        form.addRow("", self.gpu_button)

        group = QGroupBox("Performance")
        group.setObjectName("performance")
        group.setLayout(form)

        self.profile_box.currentTextChanged.connect(self.on_profile_changed)
        self.gpu_button.clicked.connect(self.on_gpu_apply_clicked)
        return group

    def build_display_group(self) -> QGroupBox:
        """Build the Display section: brightness slider, refresh rate dropdown and night light tick box"""
        self.screen_slider = QSlider(Qt.Orientation.Horizontal)
        self.screen_slider.setRange(MIN_SCREEN_BRIGHTNESS, 100)
        self.screen_value = QLabel()
        screen_brightness = get_screen_brightness()
        if screen_brightness is None:
            self.screen_slider.setEnabled(False)
            self.screen_value.setText("not supported")
        else:
            self.screen_slider.setValue(screen_brightness)
            self.screen_value.setText(f"{screen_brightness}%")

        screen_row = QHBoxLayout()
        screen_row.addWidget(self.screen_slider)
        screen_row.addWidget(self.screen_value)

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
        form.addRow("Brightness:", screen_row)
        form.addRow("Refresh rate:", self.refresh_box)
        form.addRow("", self.night_light_box)

        group = QGroupBox("Display")
        group.setObjectName("display")
        group.setLayout(form)

        self.screen_slider.valueChanged.connect(self.on_screen_brightness_changed)
        self.screen_slider.sliderReleased.connect(self.on_screen_brightness_released)
        self.refresh_box.currentTextChanged.connect(self.on_refresh_rate_changed)
        self.night_light_box.toggled.connect(self.on_night_light_toggled)
        return group

    def build_keyboard_group(self) -> QGroupBox:
        """Build the Keyboard section: brightness slider, lighting effect, colour and speed"""
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

        rgb = get_keyboard_rgb()
        self.rgb_colour = rgb["colour"]

        self.rgb_effect_box = QComboBox()
        self.rgb_effect_box.addItems(list(RGB_EFFECTS))
        self.rgb_effect_box.setCurrentText(rgb["effect"])

        self.rgb_swatch = QLabel()
        self.rgb_swatch.setFixedSize(34, 24)
        self.rgb_colour_button = QPushButton("Choose...")
        self.rgb_speed_box = QComboBox()
        self.rgb_speed_box.setObjectName("speedBox")
        self.rgb_speed_box.addItems(list(RGB_SPEEDS))
        self.rgb_speed_box.setCurrentText(rgb["speed"])

        colour_row = QHBoxLayout()
        colour_row.addWidget(self.rgb_swatch)
        colour_row.addWidget(self.rgb_colour_button)
        colour_row.addStretch()

        form = QFormLayout()
        form.addRow("Brightness:", keyboard_row)
        form.addRow("Effect:", self.rgb_effect_box)
        form.addRow("Colour:", colour_row)
        form.addRow("Speed:", self.rgb_speed_box)

        group = QGroupBox("Keyboard")
        group.setObjectName("keyboard")
        group.setLayout(form)

        self.update_rgb_controls()

        self.keyboard_slider.valueChanged.connect(self.on_keyboard_changed)
        self.rgb_effect_box.currentTextChanged.connect(self.on_rgb_changed)
        self.rgb_speed_box.currentTextChanged.connect(self.on_rgb_changed)
        self.rgb_colour_button.clicked.connect(self.on_rgb_colour_clicked)
        return group

    def update_rgb_controls(self) -> None:
        """Show the chosen colour in the swatch, and grey out colour or speed when the effect ignores them"""
        effect = self.rgb_effect_box.currentText()
        uses_colour = effect in EFFECTS_WITH_COLOUR
        self.rgb_swatch.setStyleSheet(
            f"background: {self.rgb_colour if uses_colour else 'transparent'};"
            "border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 6px;"
        )
        self.rgb_colour_button.setEnabled(uses_colour)
        self.rgb_speed_box.setEnabled(effect in EFFECTS_WITH_SPEED)

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

    def build_live_group(self) -> QGroupBox:
        """Build the Live section: sensor readings that update every second, two of them with graphs"""
        theme = THEMES[get_theme_name()]
        self.cpu_usage = CpuUsage()

        self.temp_value = QLabel("...")
        self.temp_graph = Sparkline(30, 100, theme["SECTION_1"])
        self.usage_value = QLabel("...")
        self.usage_graph = Sparkline(0, 100, theme["SECTION_4"])
        self.fans_value = QLabel("...")
        self.power_value = QLabel("...")
        self.nvidia_value = QLabel("...")

        live_grid = QGridLayout()
        live_grid.setColumnMinimumWidth(1, 70)
        live_grid.setColumnStretch(2, 1)
        live_grid.setHorizontalSpacing(14)
        live_grid.addWidget(QLabel("CPU temperature:"), 0, 0)
        live_grid.addWidget(self.temp_value, 0, 1)
        live_grid.addWidget(self.temp_graph, 0, 2)
        live_grid.addWidget(QLabel("CPU usage:"), 1, 0)
        live_grid.addWidget(self.usage_value, 1, 1)
        live_grid.addWidget(self.usage_graph, 1, 2)
        live_grid.addWidget(QLabel("Fans:"), 2, 0)
        live_grid.addWidget(self.fans_value, 2, 1, 1, 2)
        live_grid.addWidget(QLabel("Power draw:"), 3, 0)
        live_grid.addWidget(self.power_value, 3, 1, 1, 2)
        live_grid.addWidget(QLabel("Nvidia GPU:"), 4, 0)
        live_grid.addWidget(self.nvidia_value, 4, 1, 1, 2)
        live_grid.setRowStretch(0, 1)
        live_grid.setRowStretch(1, 1)

        group = QGroupBox("Live")
        group.setObjectName("live")
        group.setLayout(live_grid)
        return group

    def refresh_sensors(self) -> None:
        """Runs every second: read the sensors, update the numbers and feed the graphs"""
        temperature = get_cpu_temperature()
        if temperature is None:
            self.temp_value.setText("not supported")
        else:
            self.temp_value.setText(f"{temperature:.0f} °C")
            self.temp_graph.add_value(temperature)

        usage = self.cpu_usage.read()
        if usage is None:
            self.usage_value.setText("not supported")
        else:
            self.usage_value.setText(f"{usage:.0f} %")
            self.usage_graph.add_value(usage)

        fans = get_fan_speeds()
        if fans is None:
            self.fans_value.setText("not supported")
        else:
            self.fans_value.setText(f"CPU {fans[0]} RPM  ·  GPU {fans[1]} RPM")

        power = get_power_draw()
        self.power_value.setText("on AC power" if power is None else f"{power:.1f} W")

        awake = is_nvidia_awake()
        if awake is None:
            self.nvidia_value.setText("off")
        else:
            self.nvidia_value.setText("awake" if awake else "asleep")

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
        bus.add_signal_receiver(
            self.on_upower_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface=PROPERTIES,
            bus_name=UPOWER,
            path=UPOWER_PATH,
        )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_from_system)
        self.sensor_timer = QTimer(self)
        self.sensor_timer.timeout.connect(self.refresh_sensors)

    def on_profile_properties_changed(self, interface, changed, invalidated) -> None:
        """The system says the profile changed: show it without applying it again"""
        if "ActiveProfile" not in changed:
            return
        blocker = QSignalBlocker(self.profile_box)
        self.profile_box.setCurrentText(str(changed["ActiveProfile"]))
        del blocker

    def on_autostart_toggled(self, checked: bool) -> None:
        """Runs when Start at login is ticked or unticked. Puts the box back if the change failed"""
        ok = set_autostart(checked)
        if ok:
            self.show_result(True, "Will start at login" if checked else "Will not start at login")
            return
        blocker = QSignalBlocker(self.autostart_box)
        self.autostart_box.setChecked(is_autostart_enabled())
        del blocker
        self.show_result(False, "Could not change the start at login setting")

    def on_upower_properties_changed(self, interface, changed, invalidated) -> None:
        """The system says something about the power supply changed: pass on whether we are on battery"""
        if "OnBattery" in changed:
            self.on_power_source_changed(bool(changed["OnBattery"]))

    def on_power_source_changed(self, on_battery: bool) -> None:
        """Runs when the charger is plugged in or unplugged. Acts only if the power source really changed"""
        if on_battery == self.on_battery:
            return
        self.on_battery = on_battery

        name = choose_preset(on_battery, self.auto_box.isChecked(), self.charger_box.currentText(), self.battery_box.currentText())
        if name is None:
            return

        applied, failed = apply_preset(name)
        self.refresh_from_system()
        source = "On battery" if on_battery else "On charger"
        if failed == 0:
            self.show_result(True, f"{source}: switched to {name}")
        else:
            self.show_result(False, f"{source}: {name} profile, {applied} applied, {failed} failed")
        self.notify(self.status_label.text())

    def on_battery_properties_changed(self, interface, changed, invalidated) -> None:
        """The system says the battery level or state changed: refresh the level text"""
        if "Percentage" in changed or "State" in changed:
            self.battery_label.setText(self.battery_text())

    def refresh_from_system(self) -> None:
        """Runs on the timer: re-read the settings and update the widgets quietly.

        The profile is checked here too, although it also has a D-Bus signal: when this app itself
        changes the profile, that signal can arrive late, so this keeps the dropdown right.
        """
        profile = get_profile()
        if profile is not None and profile != self.profile_box.currentText():
            blocker = QSignalBlocker(self.profile_box)
            self.profile_box.setCurrentText(profile)
            del blocker

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

        screen_brightness = get_screen_brightness()
        if screen_brightness is not None and not self.screen_slider.isSliderDown() and screen_brightness != self.screen_slider.value():
            blocker = QSignalBlocker(self.screen_slider)
            self.screen_slider.setValue(screen_brightness)
            del blocker
            self.screen_value.setText(f"{screen_brightness}%")

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

        state = {"profile": profile, "refresh_rate": rate, "keyboard_brightness": brightness}
        self.show_preset(find_matching_preset(state))

    def show_result(self, ok: bool, message: str) -> None:
        """Show the outcome of the last action in the status line"""
        self.status_label.setText(f"{'✓' if ok else '✗'} {message}")

    def on_preset_chosen(self, name: str) -> None:
        """Runs when the user picks a profile. Applies it, then makes the controls show the new state"""
        if name == CUSTOM:
            self.refresh_from_system()
            return
        applied, failed = apply_preset(name)
        self.refresh_from_system()
        if failed == 0:
            self.show_result(True, f"{name} profile applied")
        else:
            self.show_result(False, f"{name} profile: {applied} applied, {failed} failed")

    def on_theme_changed(self, name: str) -> None:
        """Re-colour the whole app with the chosen theme and remember the choice"""
        QApplication.instance().setStyleSheet(build_style(name))
        self.temp_graph.set_colour(THEMES[name]["SECTION_1"])
        self.usage_graph.set_colour(THEMES[name]["SECTION_4"])
        save_setting("theme", name)
        self.show_result(True, f"Theme changed to {name}")

    def on_profile_changed(self, text: str) -> None:
        ok = set_profile(text)
        self.show_result(ok, f"Power mode set to {text}" if ok else f"Could not set power mode to {text}")
        self.show_preset(find_matching_preset(self.current_state()))

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
        self.show_preset(find_matching_preset(self.current_state()))

    def on_screen_brightness_changed(self, value: int) -> None:
        """Runs while the slider moves: the screen follows it live"""
        self.screen_value.setText(f"{value}%")
        if not set_screen_brightness(value):
            self.show_result(False, "Could not set screen brightness")

    def on_screen_brightness_released(self) -> None:
        self.show_result(True, f"Screen brightness set to {self.screen_slider.value()}%")

    def on_night_light_toggled(self, checked: bool) -> None:
        ok = set_night_light(checked)
        state = "on" if checked else "off"
        self.show_result(ok, f"Night light turned {state}" if ok else f"Could not turn night light {state}")

    def on_rgb_colour_clicked(self) -> None:
        """Open the colour picker. Apply the colour if the user chose one, do nothing if they cancelled"""
        chosen = QColorDialog.getColor(QColor(self.rgb_colour), self, "Keyboard colour")
        if not chosen.isValid():
            return
        self.rgb_colour = chosen.name()
        self.on_rgb_changed()

    def on_rgb_changed(self, text: str = "") -> None:
        """Runs when the effect, colour or speed changes: send all three to the keyboard"""
        effect = self.rgb_effect_box.currentText()
        ok = set_keyboard_rgb(effect, self.rgb_colour, self.rgb_speed_box.currentText())
        self.update_rgb_controls()
        if not ok:
            self.show_result(False, "Could not set keyboard lighting")
        elif self.keyboard_slider.value() == 0:
            self.show_result(True, f"Keyboard lighting set to {effect}. Raise Brightness to see it")
        else:
            self.show_result(True, f"Keyboard lighting set to {effect}")

    def on_keyboard_changed(self, value: int) -> None:
        self.keyboard_value.setText(str(value))
        ok = set_keyboard_brightness(value)
        self.show_result(ok, f"Keyboard set to {value}" if ok else "Could not set keyboard brightness")
        self.show_preset(find_matching_preset(self.current_state()))

    def on_charge_dragged(self, value: int) -> None:
        """Only updates the number while dragging; nothing is applied yet"""
        self.charge_value.setText(f"{value}%")

    def on_charge_released(self) -> None:
        value = self.charge_slider.value()
        ok = set_charge_limit(value)
        self.show_result(ok, f"Charge limit set to {value}%" if ok else "Could not set charge limit")


def main() -> None:
    """Start the dashboard. This is what the asus-dashboard command runs"""
    DBusGMainLoop(set_as_default=True)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    running_copy = ask_running_copy_to_show()
    if running_copy == COPY_SHOWN:
        print("The dashboard is already running: asked it to show its window")
        sys.exit(0)
    if running_copy == COPY_STUCK:
        print("A copy of the dashboard is running but not responding (it may be suspended).")
        print("End it with:  pkill -9 -f asus-dashboard   and then start the dashboard again.")
        sys.exit(1)

    app.setApplicationName("asus-dashboard")
    app.setDesktopFileName("asus-dashboard")
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(build_style(get_theme_name()))
    window = Dashboard()
    if "--hidden" not in sys.argv:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
