from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from tools.helpers import Helper
from tools.macros import Const, PLAYER_NAME
from views.advantage_chart import AdvantageChart


class RecordPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("recordPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(220)
        self.setFixedHeight(600)
        Helper.load_stylesheet(self, "record_panel.qss")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        title = QLabel("本局棋谱")
        title.setObjectName("recordTitle")
        self.count_label = QLabel("共 0 手")
        self.empty_label = QLabel("暂无落子，黑方先行")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["手数", "执棋方", "坐标"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        layout.addWidget(title)
        layout.addWidget(self.count_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table, 1)
        self.analysis_label = QLabel("局势分析 · +0.0")
        self.chart = AdvantageChart()
        note = QLabel("棋型评估指数，非胜率")
        layout.addWidget(self.analysis_label)
        layout.addWidget(self.chart)
        layout.addWidget(note)

    def refresh(self, moves, evaluations):
        self.chart.set_values(evaluations)
        self.analysis_label.setText(f"局势分析 · {evaluations[-1]:+.1f}")
        self.count_label.setText(f"共 {len(moves)} 手")
        self.empty_label.setVisible(not moves)
        self.table.setRowCount(len(moves))
        for row, move in enumerate(moves):
            # Match the board: O at the top, A at the bottom; columns 1–15.
            coordinate = f"{chr(ord('A') + Const.BOARD_SIZE - 1 - move.point.x)}{move.point.y + 1}"
            for col, text in enumerate((str(move.step), PLAYER_NAME[move.player], coordinate)):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
        if moves:
            self.table.selectRow(len(moves) - 1)
            self.table.scrollToBottom()
