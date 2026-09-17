from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from UI.chess_board_widget import ChessBoardWidget
from UI.game_toolbar import GameToolbar


class GameWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 整体纵向布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = GameToolbar()
        main_layout.addWidget(self.toolbar)

        # Toolbar 下方的内容区域
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 0, 0, 0)
        content_layout.setSpacing(0)

        # 左侧棋盘区域
        board_area = QWidget()
        board_layout = QVBoxLayout(board_area)
        board_layout.setContentsMargins(0, 0, 0, 0)

        self.chess_board = ChessBoardWidget()

        board_layout.addWidget(
            self.chess_board,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # 右侧棋谱区域
        self.record_panel = QWidget()

        # 添加到横向布局
        content_layout.addWidget(board_area)
        content_layout.addWidget(self.record_panel)

        main_layout.addWidget(content_widget)