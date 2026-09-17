from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
)

from PySide6.QtCore import Qt


from Tools.helper import Helper
from PySide6.QtGui import QPalette

class GameToolbar(QWidget):
    def __init__(self):
        super().__init__()
        Helper.load_stylesheet(self, "game_toolbar.qss")

        self.setFixedHeight(50)

        # 设置工具栏背景
        self.setObjectName("gameToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 新局
        self.new_game_button = QPushButton("新局")

        # 悔棋
        self.undo_button = QPushButton("悔棋")

        # AI 提示
        self.hint_button = QPushButton("提示")

        # 保存棋谱
        self.save_record_button = QPushButton("保存棋谱")

        # 保存棋谱
        self.back_button = QPushButton("返回主界面")

        # 状态
        self.status_label = QLabel("黑方回合")

        layout.addWidget(self.new_game_button)
        layout.addWidget(self.undo_button)
        layout.addWidget(self.hint_button)
        layout.addWidget(self.save_record_button)
        layout.addWidget(self.back_button)

        # 把状态推到右侧
        layout.addStretch()

        layout.addWidget(self.status_label)

