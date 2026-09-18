from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)

from Tools.helpers import Helper
from Tools.macros import Const
from Views.chess_board_canvas import ChessBoardCanvas

class ChessBoardWidget(QWidget):
    def __init__(self):
        super().__init__()
        Helper.load_stylesheet(self, "chess_board_widget.qss")

        self.setObjectName("chessBoard")
        self.setFixedSize(600, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # =========================
        # 上方数字
        # =========================

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 0, 0, 0)
        top_layout.setSpacing(0)

        for number in range(1, 16):
            label = QLabel(str(number))
            label.setFixedWidth(Const.CELL_SIZE)
            label.setAlignment(
                Qt.AlignmentFlag.AlignTop |
                Qt.AlignmentFlag.AlignHCenter
            )
            top_layout.addWidget(label)

        main_layout.addLayout(top_layout)

        # =========================
        # 左侧字母 + 棋盘
        # =========================

        board_layout = QHBoxLayout()
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(0)

        # =========================
        # 左侧字母
        # =========================

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        for letter in reversed("ABCDEFGHIJKLMNO"):
            label = QLabel(letter)
            label.setFixedHeight(Const.CELL_SIZE)
            label.setAlignment(
                Qt.AlignmentFlag.AlignVCenter |
                Qt.AlignmentFlag.AlignLeft
            )
            left_layout.addWidget(label)

        board_layout.addLayout(left_layout)

        # =========================
        # 棋盘
        # =========================
        self.board_area = ChessBoardCanvas()
        self.board_area.setFixedSize(
            Const.CELL_SIZE * 15,
            Const.CELL_SIZE * 15
        )

        board_layout.addWidget(self.board_area, alignment=Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
        self.setLayout(board_layout)

        main_layout.addLayout(board_layout)