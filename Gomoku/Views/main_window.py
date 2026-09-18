from PySide6.QtWidgets import QMainWindow, QWidget

from Tools.macros import GameMode
from Tools.helpers import Helper
from Views import start_widget, game_widget

from Tools.signals import nav_signal


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.game_widget = None
        Helper.load_stylesheet(self, "main_window.qss")

        self.setWindowTitle("Gomoku")
        self.setFixedSize(900, 700)

        self.start_widget = start_widget.StartWidget()
        self.setCentralWidget(self.start_widget)

        self.start_widget.start_game_signal.connect(self.start_game)
        nav_signal.nav_to_start_widget_signal.connect(self.nav_to_start_widget)

    def start_game(self, mode: GameMode):
        self.game_widget = game_widget.GameWidget()
        self.setCentralWidget(self.game_widget)

    def nav_to_start_widget(self):
        self.start_widget = start_widget.StartWidget()
        self.setCentralWidget(self.start_widget)
        self.start_widget.start_game_signal.connect(self.start_game)