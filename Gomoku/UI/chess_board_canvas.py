from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class ChessBoardCanvas(QWidget):
    BOARD_SIZE = 15
    CELL_SIZE = 36

    def __init__(self):
        super().__init__()

        self.setFixedSize(
            self.BOARD_SIZE * self.CELL_SIZE,
            self.BOARD_SIZE * self.CELL_SIZE
        )

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 棋盘线
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(1)
        painter.setPen(pen)

        board_size = self.BOARD_SIZE
        cell_size = self.CELL_SIZE

        # 横线
        for row in range(board_size):
            y = row * cell_size + cell_size // 2

            painter.drawLine(
                cell_size // 2,
                y,
                cell_size * (board_size - 1) + cell_size // 2,
                y
            )

        # 竖线
        for col in range(board_size):
            x = col * cell_size + cell_size // 2

            painter.drawLine(
                x,
                cell_size // 2,
                x,
                cell_size * (board_size - 1) + cell_size // 2
            )