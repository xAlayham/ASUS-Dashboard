"""Colour themes for the dashboard.

Each theme is a dict of colour names to colours. style.qss contains placeholders such as
@TEXT@ and @ACCENT@; build_style() in dashboard.py swaps each one for the value below.

The WINDOW_TOP and WINDOW_BOTTOM colours are rgba(): their last number is how solid the
window is (0 = fully see-through, 1 = solid).
"""

DEFAULT_THEME = "Mocha"

THEMES = {
    # Soft purple-blue with pastel accents
    "Mocha": {
        "WINDOW_TOP": "rgba(30, 30, 46, 0.84)",
        "WINDOW_BOTTOM": "rgba(24, 24, 37, 0.90)",
        "TEXT": "#cdd6f4",
        "MUTED": "#a6adc8",
        "CARD": "rgba(49, 50, 68, 0.55)",
        "CARD_BORDER": "rgba(205, 214, 244, 0.10)",
        "INPUT": "rgba(17, 17, 27, 0.55)",
        "POPUP": "#1e1e2e",
        "ACCENT": "#cba6f7",
        "ACCENT_DARK": "#8f6fc4",
        "SECTION_1": "#fab387",
        "SECTION_2": "#f38ba8",
        "SECTION_3": "#a6e3a1",
        "SECTION_4": "#89b4fa",
    },
    # Dark graphite with warm amber
    "Amber": {
        "WINDOW_TOP": "rgba(52, 40, 30, 0.84)",
        "WINDOW_BOTTOM": "rgba(23, 23, 26, 0.90)",
        "TEXT": "#f0ece6",
        "MUTED": "#a89f94",
        "CARD": "rgba(70, 62, 54, 0.50)",
        "CARD_BORDER": "rgba(255, 255, 255, 0.10)",
        "INPUT": "rgba(0, 0, 0, 0.32)",
        "POPUP": "#26221f",
        "ACCENT": "#ffa63d",
        "ACCENT_DARK": "#c9781c",
        "SECTION_1": "#ffa63d",
        "SECTION_2": "#ff7a59",
        "SECTION_3": "#f2c94c",
        "SECTION_4": "#e0a070",
    },
    # Dark slate with mint
    "Teal": {
        "WINDOW_TOP": "rgba(18, 56, 58, 0.84)",
        "WINDOW_BOTTOM": "rgba(14, 28, 34, 0.90)",
        "TEXT": "#e6f1f0",
        "MUTED": "#8fb0ad",
        "CARD": "rgba(36, 72, 74, 0.50)",
        "CARD_BORDER": "rgba(230, 241, 240, 0.10)",
        "INPUT": "rgba(4, 16, 20, 0.45)",
        "POPUP": "#152c30",
        "ACCENT": "#3fd6b8",
        "ACCENT_DARK": "#1f9c86",
        "SECTION_1": "#3fd6b8",
        "SECTION_2": "#5cc8f0",
        "SECTION_3": "#9be28a",
        "SECTION_4": "#7fb7ff",
    },
    # Deep navy with soft blue
    "Midnight": {
        "WINDOW_TOP": "rgba(38, 32, 74, 0.84)",
        "WINDOW_BOTTOM": "rgba(18, 22, 40, 0.90)",
        "TEXT": "#e8ebf4",
        "MUTED": "#98a2bd",
        "CARD": "rgba(48, 52, 92, 0.50)",
        "CARD_BORDER": "rgba(232, 235, 244, 0.10)",
        "INPUT": "rgba(8, 10, 24, 0.45)",
        "POPUP": "#1e2440",
        "ACCENT": "#5b8cff",
        "ACCENT_DARK": "#3a63d1",
        "SECTION_1": "#5b8cff",
        "SECTION_2": "#b388ff",
        "SECTION_3": "#57d3c0",
        "SECTION_4": "#ff8fb1",
    },
}
