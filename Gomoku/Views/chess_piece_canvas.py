from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import QWidget, QMessageBox

from models import data_model
from tools.macros import Const, PlaceResult, PLAYER_NAME, GameMode, Player
from controllers import play_game_controller
from tools.signals import nav_signal


def nav_to_start_widget():
    nav_signal.nav_to_start_widget_signal.emit()

class ChessPieceCanvas(QWidget):
    game_changed = Signal()
    game_finished = Signal(object, object)

    play_game_controller: play_game_controller.PlayGameController

    def __init__(self, mode=GameMode.TWO_PLAYERS):
        super().__init__()
        self.mode = mode
        self.hint_point = None

        self.continue_button = None
        self.main_menu_button = None
        self.msg_box = None
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
        self.update_hover(event.position())

    def update_hover(self, position):
        if self.play_game_controller.is_game_over() or (
            self.mode == GameMode.AI
            and self.play_game_controller.game_model.current_player == Player.WHITE
        ):
            self.clear_hover()
            return

        x = position.x()
        y = position.y()

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

        self.update_hover(event.position())
        if not self.can_place:
            return

        point = data_model.Point(
            self.hover_row,
            self.hover_col
        )

        self.place_stone(point)

    def place_stone(self, point):
        result = self.play_game_controller.place_stone(point)
        self.hint_point = None
        self.clear_hover()
        if result != PlaceResult.INVALID:
            self.game_changed.emit()

        if result in (PlaceResult.WIN, PlaceResult.DRAW):
            model = self.play_game_controller.game_model
            self.game_finished.emit(model.winner, model.game_mode)
            self.msg_box = QMessageBox(self)

            self.msg_box.setWindowTitle("游戏结束")
            self.msg_box.setText(
                "棋盘已满，本局和棋！"
                if result == PlaceResult.DRAW
                else f"{PLAYER_NAME[self.play_game_controller.game_model.winner]}获胜！"
            )

            self.main_menu_button = self.msg_box.addButton(
                "返回主菜单",
                QMessageBox.ButtonRole.RejectRole
            )

            self.continue_button = self.msg_box.addButton(
                "再来一局",
                QMessageBox.ButtonRole.AcceptRole
            )

            self.msg_box.buttonClicked.connect(
                self.on_game_over_button_clicked
            )

            self.msg_box.open()

    def on_game_over_button_clicked(self, button):
        if button == self.main_menu_button:
            nav_to_start_widget()

        elif button == self.continue_button:
            self.restart_game()

    def restart_game(self):
        self.play_game_controller.play_new_game(self.mode)
        self.hint_point = None
        self.clear_hover()
        self.game_changed.emit()

    def undo_move(self):
        moves = self.play_game_controller.game_model.moves
        undo_pair = self.mode == GameMode.AI and moves and moves[-1].player == Player.WHITE
        if self.play_game_controller.undo_move():
            if undo_pair:
                self.play_game_controller.undo_move()
            self.hint_point = None
            self.clear_hover()
            self.game_changed.emit()

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
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )
        self.paint_stones(painter)
        if self.hint_point is not None:
            painter.setPen(QPen(QColor("#19766D"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(
                self.hint_point.y * Const.CELL_SIZE + Const.OFFSET_SIZE,
                self.hint_point.x * Const.CELL_SIZE + Const.OFFSET_SIZE,
            ), 11, 11)

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
