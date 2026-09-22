from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
)

from tools.macros import GameMode
from tools.helpers import Helper

class StartWidget(QWidget):
    start_game_signal = Signal(GameMode)
    settings_requested = Signal()

    def __init__(self):
        super().__init__()

        self.init_ui()
        Helper.load_stylesheet(self, "start_widget.qss")

    def init_ui(self):
        # =========================
        # 主布局
        # =========================
        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # =========================
        # 标题
        # =========================
        title = QLabel("Gomoku")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("title")

        subtitle = QLabel("五子棋")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("subtitle")

        # =========================
        # 按钮
        # =========================
        ai_player_button = QPushButton("AI 对弈")
        two_player_button = QPushButton("双人对弈")
        settings_button = QPushButton("设置")
        self.settings_button = settings_button
        exit_button = QPushButton("退出")

        ai_player_button.setObjectName("startBtn")
        two_player_button.setObjectName("startBtn")
        settings_button.setObjectName("settingsBtn")
        exit_button.setObjectName("exitBtn")

        # 固定按钮大小
        for button in (ai_player_button,
                       two_player_button,
                       settings_button,
                       exit_button):

            button.setFixedSize(240, 50)

        # =========================
        # 按钮区域
        # =========================
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button_layout.addWidget(ai_player_button)
        button_layout.addWidget(two_player_button)
        button_layout.addWidget(settings_button)
        button_layout.addWidget(exit_button)

        # =========================
        # 添加到主布局
        # =========================
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(35)
        layout.addLayout(button_layout)
        layout.addStretch()

        # =========================
        # 信号
        # =========================
        ai_player_button.clicked.connect(
            lambda: self.start_game_signal.emit(GameMode.AI)
        )

        two_player_button.clicked.connect(
            lambda: self.start_game_signal.emit(GameMode.TWO_PLAYERS)
        )

        settings_button.clicked.connect(self.settings_requested.emit)
        exit_button.clicked.connect(lambda: self.window().close())
