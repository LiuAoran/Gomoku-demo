from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class AdvantageChart(QWidget):
    """Fixed scale: black advantage above zero, white advantage below zero."""
    def __init__(self):
        super().__init__()
        self.values = [0.0]
        self.setFixedHeight(172)
        self.setMouseTracking(True)
        self.setToolTip("正值：黑方优势；负值：白方优势。棋型评估指数，不代表胜率。")

    def set_values(self, values):
        self.values = list(values)
        self.update()

    def plot_rect(self):
        return QRectF(35, 23, max(1, self.width() - 47), self.height() - 52)

    def mouseMoveEvent(self, event):
        rect = self.plot_rect()
        if rect.contains(event.position()):
            step = round((event.position().x() - rect.left()) / rect.width() * max(10, len(self.values) - 1))
            if 0 <= step < len(self.values):
                self.setToolTip(f"第 {step} 手 · 优势指数 {self.values[step]:+.1f}（正黑 / 负白，非胜率）")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FBF4E6"))
        rect = self.plot_rect()
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor("#4A3424"))
        painter.drawText(QRectF(5, 1, self.width() - 10, 20), "黑优 (+) / 白优 (−)")
        for value in (-100, 0, 100):
            y = rect.center().y() - value / 100 * rect.height() / 2
            painter.setPen(QPen(QColor("#B49C78" if value == 0 else "#E6D2A5"), 1,
                                Qt.PenStyle.SolidLine if value == 0 else Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(QColor("#6F675D"))
            painter.drawText(QRectF(0, y - 8, 30, 16), Qt.AlignmentFlag.AlignRight,
                             f"{value:+d}" if value else "0")
        painter.drawLine(rect.topLeft(), rect.bottomLeft())
        steps = max(10, len(self.values) - 1)
        for step in (0, steps // 2, steps):
            x = rect.left() + step / steps * rect.width()
            painter.drawText(QRectF(x - 14, rect.bottom() + 3, 28, 16),
                             Qt.AlignmentFlag.AlignCenter, str(step))
        painter.drawText(QRectF(0, self.height() - 14, self.width(), 14),
                         Qt.AlignmentFlag.AlignRight, "步数 →")
        path = QPainterPath()
        for step, value in enumerate(self.values):
            point = QPointF(rect.left() + step / steps * rect.width(),
                            rect.center().y() - value / 100 * rect.height() / 2)
            if step == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        painter.setPen(QPen(QColor("#19766D"), 2))
        painter.drawPath(path)
        painter.setBrush(QColor("#19766D"))
        painter.drawEllipse(point, 3, 3)
