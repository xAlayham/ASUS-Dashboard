from collections import deque

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class Sparkline(QWidget):
    """A small line graph of the most recent values, with a faint fill under the line."""

    def __init__(self, minimum: float, maximum: float, colour: str, size: int = 60):
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum
        self.colour = QColor(colour)
        self.values = deque(maxlen=size)
        self.setMinimumSize(160, 36)

    def set_colour(self, colour: str) -> None:
        """Change the line colour, for example after a theme change, and redraw"""
        self.colour = QColor(colour)
        self.update()

    def add_value(self, value: float) -> None:
        """Add the newest reading and redraw. The oldest one drops off when the graph is full"""
        self.values.append(value)
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the stored values as a line from left (oldest) to right (newest)"""
        if len(self.values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 2
        height = self.height() - 2 * margin
        step = self.width() / (self.values.maxlen - 1)
        span = self.maximum - self.minimum

        line = QPainterPath()
        last_x = 0.0
        for index, value in enumerate(self.values):
            clamped = min(max(value, self.minimum), self.maximum)
            x = index * step
            y = margin + height - (clamped - self.minimum) / span * height
            if index == 0:
                line.moveTo(QPointF(x, y))
            else:
                line.lineTo(QPointF(x, y))
            last_x = x

        fill = QPainterPath(line)
        fill.lineTo(QPointF(last_x, self.height()))
        fill.lineTo(QPointF(0, self.height()))
        fill.closeSubpath()
        fill_colour = QColor(self.colour)
        fill_colour.setAlpha(40)
        painter.fillPath(fill, fill_colour)

        painter.setPen(QPen(self.colour, 2))
        painter.drawPath(line)
