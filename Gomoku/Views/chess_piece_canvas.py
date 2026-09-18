from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QMessageBox

from Models import data_model
from Tools.macros import Const, PlaceResult, PLAYER_NAME, GameMode
from Controllers import play_game_controller
from Tools.signals import nav_signal


def nav_to_start_widget():
    nav_signal.nav_to_start_widget_signal.emit()


class ChessPieceCanvas(QWidget):

    play_game_controller: play_game_controller.PlayGameController

    def __init__(self):
        super().__init__()

        self.setFixedSize(
            Const.BOARD_SIZE * Const.CELL_SIZE,
            Const.BOARD_SIZE * Const.CELL_SIZE
        )

        # 透明背景
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        # 鼠标悬浮追踪
        self.setMouseTracking(True)

        # 当前悬浮位置
        self.hover_row = -1
        self.hover_col = -1

        # 当前是否可以落子
        self.can_place = False

        # 游戏控制器
        self.play_game_controller = (
            play_game_controller.PlayGameController()
        )

        self.restart_game()


    # =========================
    # 鼠标事件
    # =========================

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        self.can_place = False

        # 转换成棋盘坐标
        col = round(
            (x - Const.OFFSET_SIZE)
            / Const.CELL_SIZE
        )

        row = round(
            (y - Const.OFFSET_SIZE)
            / Const.CELL_SIZE
        )

        # 检查是否在棋盘范围
        if not (
            0 <= row < Const.BOARD_SIZE
            and 0 <= col < Const.BOARD_SIZE
        ):
            self.clear_hover()
            return

        # 最近交点坐标
        point_x = (
            col * Const.CELL_SIZE
            + Const.OFFSET_SIZE
        )

        point_y = (
            row * Const.CELL_SIZE
            + Const.OFFSET_SIZE
        )

        # 鼠标距离交点的距离
        dx = x - point_x
        dy = y - point_y

        distance = (dx * dx + dy * dy) ** 0.5

        # 判断是否可以落子
        if (
            distance <= 10
            and not self.play_game_controller.is_exist_stone(
                data_model.Point(row, col)
            )
        ):
            self.can_place = True
            self.hover_row = row
            self.hover_col = col
        else:
            self.clear_hover()

        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self.can_place:
            return

        point = data_model.Point(
            self.hover_row,
            self.hover_col
        )

        if self.play_game_controller.place_stone(point) == PlaceResult.WIN:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("游戏结束")
            msg_box.setText(
                f"{PLAYER_NAME[self.play_game_controller.game_model.winner]}获胜！"
            )

            main_menu_button = msg_box.addButton(
                "返回主菜单",
                QMessageBox.ButtonRole.RejectRole
            )

            continue_button = msg_box.addButton(
                "再来一局",
                QMessageBox.ButtonRole.AcceptRole
            )

            msg_box.exec()

            if msg_box.clickedButton() == main_menu_button:
                nav_to_start_widget()

            elif msg_box.clickedButton() == continue_button:
                self.restart_game()

    def restart_game(self):
        self.play_game_controller.play_new_game(GameMode.TWO_PLAYERS)
        self.update()

    def leaveEvent(self, event):
        self.clear_hover()

    # =========================
    # 悬停状态
    # =========================

    def clear_hover(self):
        self.hover_row = -1
        self.hover_col = -1
        self.can_place = False
        self.update()

    # =========================
    # 绘制
    # =========================

    def paintEvent(self, event):
        painter = QPainter(self)
        self.paint_stones(painter)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        if self.hover_row == -1 or self.hover_col == -1:
            return
        self.paint_hover(painter)

    def paint_hover(self, painter: QPainter):
        if not self.can_place:
            return

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

    def paint_stones(self, painter: QPainter):
        board = self.play_game_controller.game_model.board

        radius = Const.CELL_SIZE // 2 - 4

        for row in range(Const.BOARD_SIZE):
            for col in range(Const.BOARD_SIZE):

                player = board[row][col]

                # 没有棋子
                if player is None:
                    continue

                x = (
                        col * Const.CELL_SIZE
                        + Const.OFFSET_SIZE
                )

                y = (
                        row * Const.CELL_SIZE
                        + Const.OFFSET_SIZE
                )

                if player == data_model.Player.BLACK:
                    painter.setBrush(Qt.GlobalColor.black)

                elif player == data_model.Player.WHITE:
                    painter.setBrush(Qt.GlobalColor.white)

                painter.setPen(Qt.GlobalColor.black)

                painter.drawEllipse(
                    x - radius,
                    y - radius,
                    radius * 2,
                    radius * 2
                )

