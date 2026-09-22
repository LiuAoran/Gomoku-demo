from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ai.engine import choose_move
from ai.jev import JevError, choose_jev_move


class SearchSignals(QObject):
    finished = Signal(int, object, str)


class SearchTask(QRunnable):
    def __init__(self, token, board, player, difficulty="normal", api_key="", model="jev-latest"):
        super().__init__()
        self.token = token
        self.board = [row[:] for row in board]
        self.player = player
        self.difficulty = difficulty
        self.api_key = api_key
        self.model = model
        self.cancel = Event()
        self.signals = SearchSignals()

    @Slot()
    def run(self):
        try:
            if self.difficulty == "jev":
                point = choose_jev_move(self.board, self.player, self.api_key, self.model, self.cancel)
            else:
                point = choose_move(self.board, self.player, self.cancel, difficulty=self.difficulty)
            self.signals.finished.emit(self.token, point, "")
        except Exception as error:
            message = "Jev 请求失败，请重试" if self.difficulty == "jev" and not isinstance(error, JevError) else str(error)
            self.signals.finished.emit(self.token, None, message)
