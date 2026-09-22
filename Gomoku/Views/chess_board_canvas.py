from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from tools.macros import Const


class ChessBoardCanvas(QWidget):

    def __init__(self):
        super().__init__()

        self.setFixedSize(
            Const.BOARD_SIZE * Const.CELL_SIZE,
            Const.BOARD_SIZE * Const.CELL_SIZE
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(1)
        painter.setPen(pen)

        # 横线
        for row in range(Const.BOARD_SIZE):
            y = (
                row * Const.CELL_SIZE
                + Const.OFFSET_SIZE
            )

            painter.drawLine(
                Const.OFFSET_SIZE,
                y,
                Const.CELL_SIZE * (Const.BOARD_SIZE - 1)
                + Const.OFFSET_SIZE,
                y
            )

        # 竖线
        for col in range(Const.BOARD_SIZE):
            x = (
                col * Const.CELL_SIZE
                + Const.OFFSET_SIZE
            )

            painter.drawLine(
                x,
                Const.OFFSET_SIZE,
                x,
                Const.CELL_SIZE * (Const.BOARD_SIZE - 1)
                + Const.OFFSET_SIZE
            )