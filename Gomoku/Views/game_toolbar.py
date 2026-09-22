from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
)

from PySide6.QtCore import Qt


from tools.helpers import Helper
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

        # 返回
        self.back_button = QPushButton("返回主界面")
        self.settings_button = QPushButton("设置")

        # 状态
        self.status_label = QLabel("黑方回合")
        self.sound_button = QPushButton("声音：关")
        self.sound_button.setCheckable(True)
        self.sound_button.setToolTip("统一开关背景音乐和输赢音效；音量及分类开关可在设置中调整")
        self.sound_button.toggled.connect(
            lambda enabled: self.sound_button.setText("声音：开" if enabled else "声音：关")
        )

        layout.addWidget(self.new_game_button)
        layout.addWidget(self.undo_button)
        layout.addWidget(self.hint_button)
        layout.addWidget(self.back_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.sound_button)

        # 把状态推到右侧
        layout.addStretch()

        layout.addWidget(self.status_label)
