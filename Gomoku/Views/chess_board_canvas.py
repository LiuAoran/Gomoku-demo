from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from Tools.macros import Const

class ChessBoardCanvas(QWidget):
    def __init__(self):
        super().__init__()

        self.setFixedSize(
            Const.BOARD_SIZE * Const.CELL_SIZE,
            Const.BOARD_SIZE * Const.CELL_SIZE
        )
        # 开启鼠标悬浮追踪
        self.setMouseTracking(True)

        # 当前悬浮的棋盘坐标
        self.hover_row = -1
        self.hover_col = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 棋盘线
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(1)
        painter.setPen(pen)

        # 横线
        for row in range(Const.BOARD_SIZE):
            y = row * Const.CELL_SIZE + Const.OFFSET_SIZE

            painter.drawLine(
                Const.OFFSET_SIZE,
                y,
                Const.CELL_SIZE * (Const.BOARD_SIZE - 1) + Const.OFFSET_SIZE,
                y
            )

        # 竖线
        for col in range(Const.BOARD_SIZE):
            x = col * Const.CELL_SIZE + Const.OFFSET_SIZE

            painter.drawLine(
                x,
                Const.OFFSET_SIZE,
                x,
                Const.CELL_SIZE * (Const.BOARD_SIZE - 1) + Const.OFFSET_SIZE
            )

        # =========================
        # 悬浮提示
        # =========================

        if self.hover_row != -1 and self.hover_col != -1:
            x = (
                    self.hover_col * Const.CELL_SIZE
                    + Const.OFFSET_SIZE
            )

            y = (
                    self.hover_row * Const.CELL_SIZE
                    + Const.OFFSET_SIZE
            )

            pen = QPen(Qt.GlobalColor.black)
            pen.setWidth(2)
            painter.setPen(pen)

            painter.setBrush(Qt.BrushStyle.NoBrush)

            # L 型标记尺寸
            size = 7

            # 左上
            painter.drawLine(
                x - size, y - size,
                x - 3, y - size
            )
            painter.drawLine(
                x - size, y - size,
                x - size, y - 3
            )

            # 右上
            painter.drawLine(
                x + 3, y - size,
                x + size, y - size
            )
            painter.drawLine(
                x + size, y - size,
                x + size, y - 3
            )

            # 左下
            painter.drawLine(
                x - size, y + 3,
                x - size, y + size
            )
            painter.drawLine(
                x - size, y + size,
                x - 3, y + size
            )

            # 右下
            painter.drawLine(
                x + 3, y + size,
                x + size, y + size
            )
            painter.drawLine(
                x + size, y + 3,
                x + size, y + size
            )

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        # 转换成棋盘坐标
        col = round(
            (x - Const.OFFSET_SIZE)
            / Const.CELL_SIZE
        )

        row = round(
            (y - Const.OFFSET_SIZE)
            / Const.CELL_SIZE
        )

        # 判断是否在棋盘范围内
        if (
                0 <= row < Const.BOARD_SIZE
                and 0 <= col < Const.BOARD_SIZE
        ):

            # 获取最近交点的像素坐标
            point_x = (
                    col * Const.CELL_SIZE
                    + Const.OFFSET_SIZE
            )

            point_y = (
                    row * Const.CELL_SIZE
                    + Const.OFFSET_SIZE
            )

            # 计算鼠标与交点的距离
            dx = x - point_x
            dy = y - point_y

            distance = (dx * dx + dy * dy) ** 0.5

            # 距离交点 10px 以内
            if distance <= 10:
                self.hover_row = row
                self.hover_col = col
            else:
                self.hover_row = -1
                self.hover_col = -1

        else:
            self.hover_row = -1
            self.hover_col = -1

        self.update()

    def leaveEvent(self, event):
        self.hover_row = -1
        self.hover_col = -1
        self.update()