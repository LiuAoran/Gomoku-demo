from PySide6.QtWidgets import QMainWindow, QWidget

from Tools.Macro import GameMode
from Tools.Helper import Helper
from UI import start_widget, game_widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.game_widget = None
        Helper.load_stylesheet(self, "main_window.qss")

        self.setWindowTitle("Gomoku")
        self.setFixedSize(900, 700)

        self.start_widget = start_widget.StartWidget()
        self.setCentralWidget(self.start_widget)

        self.start_widget.start_game.connect(self.start_game)

    def start_game(self, mode: GameMode):
        self.game_widget = game_widget.GameWidget()
        self.setCentralWidget(self.game_widget)